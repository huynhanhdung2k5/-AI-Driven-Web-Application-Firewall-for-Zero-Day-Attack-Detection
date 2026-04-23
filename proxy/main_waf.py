from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
import httpx
import joblib
import numpy as np
from tensorflow.keras.models import load_model
import math
from collections import Counter
import pandas as pd
import warnings
import time 
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import re
warnings.filterwarnings('ignore')

# ==========================================
# ĐỘNG CƠ WEBACL ĐỘNG (DYNAMIC DYNAMIC RULE ENGINE)
# ==========================================
# Cấu trúc mới: Lưu trữ lịch sử theo từng Luật VÀ từng IP
# Định dạng: { rule_id: { "127.0.0.1": [ts1, ts2] } }
dynamic_trackers = defaultdict(lambda: defaultdict(list))
penalty_box = defaultdict(float)
attack_trackers = defaultdict(list)
error_trackers = defaultdict(lambda: defaultdict(list))
async def check_dynamic_webacl(request: Request, client_ip: str) -> dict:
    """Quét request qua tất cả các luật đang ACTIVE trong MongoDB"""
    current_time = time.time()
    jailed_info = penalty_box.get(client_ip, {})
    if jailed_info and current_time < jailed_info.get("expire", 0):
        return {
            "blocked": True,
            "rule_name": jailed_info.get("reason", "Jailed by WAF"),
            "action": "Block",
        }
    
    # 1. Kéo tất cả các luật đang có trạng thái enabled = True
    active_rules = await app.mongodb["webacl_rules"].find({"enabled": True}).to_list(length=100)
    attack_rule = [r for r in active_rules if r.get("category") == "Attack Limiting"]
    normal_rule = [r for r in active_rules if r.get("category") != "Attack Limiting"]
    is_violating = False
    violated_rule = None
    for rule in normal_rule:
        rule_id = rule["rule_id"]

        target = rule.get("match_target", "")
        operator = rule.get("operator", "")
        content = rule.get("content", "")
        
        # 2. Lấy dữ liệu từ Request để đem đi so sánh
        req_value = ""
        if target == "URL Path":
            req_value = request.url.path
        elif target == "Client IP":
            req_value = client_ip
        elif target == "User Agent":
            req_value = request.headers.get("user-agent", "")
            
        # 3. So khớp dựa trên Operator
        is_match = False
        if operator == "Equals" and req_value == content:
            is_match = True
        elif operator == "Contains" and content in req_value:
            is_match = True
        elif operator == "Matches Regex":
            try:
                if re.search(content, req_value):
                    is_match = True
            except:
                pass # Bỏ qua nếu Regex gõ sai
                
        # 4. Nếu request khớp với điều kiện, bắt đầu đếm nhịp độ (Rate Limit)
        if is_match:
            duration = rule.get("duration_sec", 60) #fallback/default value
            max_access = rule.get("access_count", 50) #fallback/default value
            challenge_min = rule.get("challenge_min", 1)
            
            # Lấy lịch sử của IP này đối với riêng luật này
            timestamps = dynamic_trackers[rule_id][client_ip]
            # Lọc bỏ các request đã cũ ngoài khung thời gian
            valid_timestamps = [ts for ts in timestamps if current_time - ts < duration]
            
            # Ghi nhận request hiện tại
            valid_timestamps.append(current_time)
            dynamic_trackers[rule_id][client_ip] = valid_timestamps
            
            # Nếu vượt ngưỡng -> CHẶN NGAY LẬP TỨC
            if len(valid_timestamps) >= max_access:
                is_violating = True
                violated_rule = rule
                break

    if is_violating :
        attack_trackers[client_ip].append(current_time)
        penalty_minutes = violated_rule.get("challenge_min", 1)
        final_rule_name = violated_rule["name"]
        final_action = violated_rule.get("action", "Block")

        for a_rule in attack_rule:
            a_duration = a_rule.get("duration_sec", 60)
            a_max_access = a_rule.get("access_count", 3)
                    
            recent_attack = [ts for ts in attack_trackers[client_ip] if current_time - ts < a_duration]
            if len(recent_attack) >= a_max_access :
                penalty_minutes = a_rule.get("challenge_min", 30)
                final_rule_name = f"{a_rule["name"]} (Escalated Penalty)"
                final_action = a_rule.get("action", "Block")
                print(f"IP {client_ip} has been penaltied for {penalty_minutes} minutes")
                break
        penalty_box[client_ip] = {
            "expire": current_time + (penalty_minutes * 60),
            "reason": final_rule_name
        }
        return {
            "blocked": True,
            "rule_name": final_rule_name,
            "action": final_action,
             }
    # Nếu đi qua hết các luật mà không bị sao -> An toàn
    return {"blocked": False}

async def check_error_limiting(client_ip: str, status_code: int):
    """Hàm này chạy SAU KHI server đích đã trả về response"""
    current_time = time.time()
    
    # 1. Kéo các luật Error Limiting đang bật
    active_rules = await app.mongodb["webacl_rules"].find({
        "enabled": True, 
        "category": "Error Limiting"
    }).to_list(length=100)
    
    str_status = str(status_code)
    
    for rule in active_rules:
        rule_id = rule["rule_id"]
        target_errors = rule.get("content", "") # Ví dụ: "403,404,500"
        
        # 2. Nếu status_code nằm trong danh sách theo dõi
        if str_status in target_errors:
            duration = rule.get("duration_sec", 60)
            max_access = rule.get("access_count", 10)
            challenge_min = rule.get("challenge_min", 30)
            
            timestamps = error_trackers[rule_id][client_ip]
            valid_timestamps = [ts for ts in timestamps if current_time - ts < duration]
            valid_timestamps.append(current_time)
            error_trackers[rule_id][client_ip] = valid_timestamps
            
            # 3. NẾU VƯỢT NGƯỠNG -> TỐNG VÀO NHÀ GIAM
            if len(valid_timestamps) >= max_access:
                # Dùng cấu trúc dict mới của penalty_box mà bạn đã cập nhật
                penalty_box[client_ip] = {
                    "expire": current_time + (challenge_min * 60),
                    "reason": rule["name"]
                }
                print(f" [ERROR LIMIT] IP {client_ip} has been denied for {challenge_min} minutes")
                break

app = FastAPI(title="AI-Driven WAF", description="Web Application Firewall for Zero-day Attack")
# Mở cổng CORS cho phép Frontend ReactJS gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép mọi nguồn gọi đến (Dùng cho môi trường Dev)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
TARGET_SERVER = "http://localhost:5001"
AE_THRESHOLD = 0.000062

# ==========================================
# MODULE 1: AI CORE & DYNAMIC BASELINE
# ==========================================
print("[*] Khởi động Module AI...")
MODEL_DIR = "../models/" 
vectorizer = joblib.load(MODEL_DIR + "tfidf_waf.pkl")
rf_model = joblib.load(MODEL_DIR + "random_forest_waf.pkl")
autoencoder = load_model(MODEL_DIR + "full_autoencoder_waf_fe.h5", compile=False)
scaler = joblib.load(MODEL_DIR + "custom_features_scaler.pkl")

print("[*] Tải Cấu hình Cơ sở Động (Dynamic Baseline Profile)...")
# Nạp thẳng 1 profile chuẩn từ CSDL để đảm bảo AI nhận diện chính xác 100%
df = pd.read_csv("../data/csic_database_cleaned.csv")
# Lọc ra tất cả các request của Người dùng thật (Target == 1)
normal_samples = df[df['Target'] == 1]['Full_Payload'].fillna('').tolist()
# Lấy bóc tách phần thân (bỏ đi URL) 
baseline_req = [req for req in normal_samples if req.startswith("GET")][0]
DYNAMIC_BASELINE = baseline_req.split(' ', 2)[2] # Trích xuất phần lõi (từ HTTP/1.1 trở đi)

# ==========================================
# MODULE 2: NORMALIZATION LAYER (LỚP CHUẨN HÓA)
# ==========================================
def reconstruct_payload(method: str, path_with_query: str, body_str: str) -> str:
    """Tái cấu trúc Request về định dạng Baseline trước khi đưa vào AI"""
    normalized_payload = f"{method} http://localhost:8080{path_with_query} {DYNAMIC_BASELINE}"
    if body_str:
        normalized_payload += f"\n\n{body_str}"
    return normalized_payload

# ==========================================
# MODULE 3: THREAT ANALYSIS (PHÂN TÍCH MỐI ĐE DỌA)
# ==========================================
def calculate_entropy(s: str) -> float:
    if not s: return 0.0
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())

def analyze_threat(payload: str) -> dict:
    """Trả về dict chứa trạng thái an toàn và lý do"""
    vector = vectorizer.transform([payload])
    dense_vector = vector.toarray()
    
    length = len(payload)
    special_chars = sum(not c.isalnum() and not c.isspace() for c in payload)
    entropy = calculate_entropy(payload)
    
    custom_features = np.array([[length, special_chars, entropy]])
    scaled_features = scaler.transform(custom_features)
    ae_input = np.hstack((dense_vector, scaled_features))

    normal_index = list(rf_model.classes_).index(1)
    rf_score = rf_model.predict_proba(vector)[0][normal_index] * 100
    
    if rf_score >= 80.0:
        return {"is_safe": True, "engine": "Random Forest", "score": rf_score}
    elif rf_score <= 30.0:
        return {"is_safe": False, "engine": "Random Forest", "reason": "Known Signature Detected"}
    else:
        ae_reconstruction = autoencoder.predict(ae_input, verbose=0)
        mse = np.mean(np.power(ae_input - ae_reconstruction, 2))
        if mse > AE_THRESHOLD:
            return {"is_safe": False, "engine": "Autoencoder", "reason": f"Zero-day Anomaly"}
        return {"is_safe": True, "engine": "Autoencoder", "score": mse}

# ==========================================
# MODULE 5: DATABASE & ASYNC LOGGING 
# ==========================================
MONGO_URL = "mongodb://localhost:27017"

@app.on_event("startup")
async def startup_db_client():
    try:
        app.mongodb_client = AsyncIOMotorClient(MONGO_URL)
        app.mongodb = app.mongodb_client.waf_db
        print("[*]  Connect successfully to MongoDB!")
    except Exception as e:
        print(f"[*]  MongoDB connection error: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()
    print("[*] Đã ngắt kết nối MongoDB.")

async def log_request_to_db(client_ip: str, method: str, path: str, http_versions: str, headers: dict, analysis: dict, payload: str, action: str, status_code: int, process_time: float ):
    try:
        # Bóc tách Header để phục vụ vẽ biểu đồ Top 10
        user_agent = headers.get('user-agent', 'Unknown')
        host = headers.get('host', 'Unknown')
        
        # Phân loại Attack Type dựa trên AI Engine
        attack_type = "None"
        if action == "BLOCKED":
            if analysis["engine"] == "Autoencoder":
                attack_type = "Zero-Day Threat"
            elif analysis["engine"] == "Random Forest":
                attack_type = "Known Signature Threat"
            elif analysis["engine"] == "Rate Limiter":
                attack_type = "HTTP Flood/DoS Attempt"
            elif analysis["engine"] == "WebACL Rules":
                attack_type = "Violated WebACL Rules"

        log_document = {
            "timestamp": datetime.now(),
            "client_ip": client_ip,
            "method": method,
            "path_accessed": path,
            "http_versions": http_versions,
            "host": host,
            "user_agent": user_agent,
            "action": action, # 'PASSED' hoặc 'BLOCKED'
            "blocked_by_engine": analysis.get("engine", "None"),
            "attack_type": attack_type,
            "reason": analysis.get("reason", "Safe Traffic"),
            "raw_payload": payload,
            "status_code": status_code,
            "process_time": round(process_time, 2),
        }
        # Lưu vào Collection mới tên là 'traffic_logs'
        await app.mongodb["traffic_logs"].insert_one(log_document)
        print(f"   >>> [DB]  Log recorded ({action}) IP {client_ip} to MongoDB!")
    except Exception as e:
        print(f"   >>> [DB]  Log error: {e}")


# ==========================================
# SCHEMAS CHO WEBACL RULES (Gom chung lên đầu)
# ==========================================
class RuleToggle(BaseModel):
    enabled: bool

class RuleCreate(BaseModel):
    category: str
    name: str
    desc: str
    enabled: bool = True
    match_target: str
    operator: str
    content: str
    duration_sec: int
    access_count: int
    action: str
    challenge_min: int

# ==========================================
# MODULE 6: API CHO DASHBOARD FRONTEND
# ==========================================
@app.get("/api/logs")
async def get_traffic_logs():
    """Lấy toàn bộ lịch sử (cả xanh lẫn đỏ) để Frontend vẽ biểu đồ"""
    logs = []
    cursor = app.mongodb["traffic_logs"].find().sort("timestamp", -1).limit(1000)
    
    async for document in cursor:
        document["_id"] = str(document["_id"]) 
        logs.append(document)
        
    return {
        "status": "success", 
        "total_requests": len(logs), 
        "data": logs
    }

# --- API 1: LẤY DANH SÁCH IP BỊ CHẶN (GỘP NHÓM BẰNG MONGODB AGGREGATION) ---
@app.get("/api/waf/blocked-ips")
async def get_blocked_ips():
    pipeline = [
        {"$match": {"action": {"$in": ["BLOCKED", "RATE LIMIT EXCEEDED"]}}},
        {"$group": {
            "_id": "$client_ip",
            "blockedCount": {"$sum": 1},
            "lastBlockedAt": {"$max": "$timestamp"},
            "reason": {"$last": "$reason"},
            "app": {"$last": "$host"},
            "engine": {"$last": "$blocked_by_engine"},
            "location": {"$first": "Vietnam"}
        }},
        {"$sort": {"lastBlockedAt": -1}},
        {"$limit": 50}
    ]
    
    cursor = app.mongodb["traffic_logs"].aggregate(pipeline)
    blocked_list = []
    async for doc in cursor:
        engine_name = doc.get("engine", "AI/WAF")
        if engine_name == "WebACL Rules":
            display_action = "Blocked by WebACL Rules"
        else:
            display_action = f"Blocked by {engine_name}"
        blocked_list.append({
            "id": str(doc["_id"]),
            "ip": doc["_id"],
            "location": doc["location"],
            "app": doc["app"],
            "host": doc["app"],
            "reason": doc["reason"],
            "action": display_action,
            "blockedCount": doc["blockedCount"],
            "startAt": doc["lastBlockedAt"].strftime("%Y-%m-%d %H:%M:%S")
        })
    return {"status": "success", "data": blocked_list}


# --- API 2: LẤY DANH SÁCH RULES (Hàm bị thiếu lúc nãy) ---
@app.get("/api/waf/rules")
async def get_webacl_rules():
    cursor = app.mongodb["webacl_rules"].find({}, {"_id": 0}).sort("rule_id", 1)
    rules = await cursor.to_list(length=100)
    return {"status": "success", "data": rules}


# --- API 3: TẠO RULE MỚI (Đã đổi thành POST) ---
@app.post("/api/waf/rules")
async def create_rule(rule: RuleCreate):
    new_rule = rule.dict()
    new_rule["rule_id"] = int(time.time() * 1000) 
    
    await app.mongodb["webacl_rules"].insert_one(new_rule)
    return {"status": "success", "message": "Rule created successfully", "rule_id": new_rule["rule_id"]}


# --- API 4: CẬP NHẬT TRẠNG THÁI BẬT/TẮT RULES ---
@app.put("/api/waf/rules/{rule_id}")
async def toggle_rule(rule_id: int, payload: RuleToggle):
    await app.mongodb["webacl_rules"].update_one(
        {"rule_id": rule_id}, 
        {"$set": {"enabled": payload.enabled}}
    )
    return {"status": "success", "message": f"Rule {rule_id} updated to {payload.enabled}"}

# --- API 5: XÓA RULES ---
@app.delete("/api/waf/rules/{rule_id}")
async def delete_rule(rule_id: int):
    result = await app.mongodb["webacl_rules"].delete_one(
        {"rule_id": rule_id}
    )
    if result.deleted_count == 1:
      return {"status": "success", "message":f"Rule {rule_id} has been deleted"}
    return {"status": "error", "message": "There is no rule to be deleted"}
# ==========================================
# MODULE 4: REVERSE PROXY ROUTING (ĐỊNH TUYẾN CHUYỂN TIẾP)
# ==========================================
client = httpx.AsyncClient(base_url=TARGET_SERVER)

# Chú ý: Đã bổ sung biến bg_tasks: BackgroundTasks vào hàm
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def reverse_proxy(request: Request, path: str, bg_tasks: BackgroundTasks):
    start_time = time.time()
    method = request.method
    path_with_query = request.url.path
    if request.url.query:
        path_with_query += f"?{request.url.query}"
        
    body_bytes = await request.body()
    body_str = body_bytes.decode('utf-8', errors='ignore') if body_bytes else ""
    
    normalized_payload = reconstruct_payload(method, path_with_query, body_str)
    
    analysis_result = analyze_threat(normalized_payload)
    print(f"[WAF] {method} {path_with_query} -> Phân tích bởi {analysis_result['engine']} -> An toàn: {analysis_result['is_safe']}")
    
    
    client_ip = request.headers.get("x-fake-ip", request.client.host if request.client else "Unknown")
    raw_version = request.scope.get("http_version", "1.1")
    http_version = f"HTTP/{raw_version}"
    # ---------------------------------------------------------
    # 1. KIỂM TRA WEBACL RULES (DYNAMIC TỪ MONGODB)
    # ---------------------------------------------------------
    headers_dict = dict(request.headers)
    acl_result = await check_dynamic_webacl(request, client_ip)
    
    if acl_result["blocked"]:
        rule_name = acl_result["rule_name"]
        print(f"   >>>[WEBACL] Đã chặn IP {client_ip} do vi phạm luật: {rule_name}")
        
        # Ghi log rõ ràng tên luật bị vi phạm vào DB
        analysis_mock = {"engine": "WebACL Rules", "reason": f"Triggered rule: {rule_name}"}
        process_time = (time.time() - start_time ) * 1000
        bg_tasks.add_task(log_request_to_db, client_ip, request.method, request.url.path, http_version, headers_dict, analysis_mock, "RATE LIMIT EXCEEDED", "BLOCKED", 429, process_time)
        
        # Tùy biến mã phản hồi theo Action cấu hình
        return HTMLResponse(
            content=f"<h1>Blocked by AI-WAF</h1><p>You violated Security Rule {rule_name}</p>", 
            status_code=429
        )
    headers_dict = dict(request.headers)
    

    if not analysis_result["is_safe"]:
        print(f"   >>> ❌ [BLOCK] Reason: {analysis_result.get('reason')}")
        process_time = (time.time() - start_time) * 1000
        
        # --- NÉM VIỆC GHI LOG CHO TIẾN TRÌNH CHẠY NGẦM ---
        client_ip = request.headers.get("x-fake-ip", request.client.host if request.client else "Unknown") #request.client.host if request.client else "Unknown IP"
        bg_tasks.add_task(log_request_to_db, client_ip, method, request.url.path, http_version, headers_dict, analysis_result, normalized_payload, "BLOCKED", 403, process_time)
        
        html_content = f"""
        <html>
            <body style="background-color: black; color: red; text-align: center; margin-top: 20%; font-family: monospace;">
                <h1> 403 FORBIDDEN - AI-WAF PROTECTED </h1>
                <p>Request Blocked by: {analysis_result['engine']}</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=403)
    
    print("   >>>  [PASS] Request an toàn. Đang Forward đến Server đích...")

    
    
    try:
        url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
        req = client.build_request(
            method=request.method,
            url=url,
            headers=request.headers.raw, 
            content=body_bytes
        )
        response = await client.send(req, stream=True)
        process_time = (time.time() - start_time) * 1000
        await check_error_limiting(client_ip, response.status_code)
        bg_tasks.add_task(log_request_to_db, client_ip, method, request.url.path, http_version, headers_dict, analysis_result, normalized_payload, "PASSED", response.status_code, process_time)
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=response.headers
        )
    except httpx.ConnectError:
        process_time = (time.time() - start_time) * 1000
        await check_error_limiting(client_ip, 502)
        bg_tasks.add_task(log_request_to_db, client_ip, method, request.url.path, http_version, headers_dict, analysis_result, normalized_payload, "PASSED", 502, process_time)
        return HTMLResponse(content="<h1>502 Bad Gateway</h1><p>Target Server (Port 5001) Offline.</p>", status_code = 502)


if __name__ == "__main__":
    print("="*50)
    print(" RUNNING AI-WAF ON PORT 8000 (ASYNC MODE)...")
    print("="*50)
    uvicorn.run("main_waf:app", host="0.0.0.0", port=8000, reload=True)