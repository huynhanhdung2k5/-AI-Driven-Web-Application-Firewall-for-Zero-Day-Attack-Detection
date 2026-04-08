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

from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

warnings.filterwarnings('ignore')

# ==========================================
# CẤU HÌNH RATE LIMIT (ANTI-DDOS / BRUTE-FORCE)
# ==========================================
RATE_LIMIT_WINDOW = 60  # Khung thời gian: 60 giây (1 phút)
MAX_REQUESTS_PER_WINDOW = 5  # Tối đa: 5 requests / 1 phút / 1 IP

# Bộ nhớ lưu trữ lịch sử truy cập của từng IP
# Định dạng: { "127.0.0.1": [thời_gian_1, thời_gian_2, ...] }
ip_request_tracker = defaultdict(list)

def check_rate_limit(client_ip: str) -> bool:
    """Trả về True nếu hợp lệ, False nếu vượt quá giới hạn (Bị chặn)"""
    current_time = time.time()
    
    # Lấy danh sách các mốc thời gian request của IP này
    timestamps = ip_request_tracker[client_ip]
    
    # Vứt bỏ những request đã cũ (nằm ngoài khung 60 giây gần nhất)
    valid_timestamps = [ts for ts in timestamps if current_time - ts < RATE_LIMIT_WINDOW]
    
    # Cập nhật lại danh sách sạch
    ip_request_tracker[client_ip] = valid_timestamps
    
    # Kiểm tra số lượng
    if len(valid_timestamps) >= MAX_REQUESTS_PER_WINDOW:
        return False # Bị chặn!
        
    # Nếu chưa quá giới hạn, ghi nhận thêm lần truy cập này
    ip_request_tracker[client_ip].append(current_time)
    return True

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
            return {"is_safe": False, "engine": "Autoencoder", "reason": f"Zero-day Anomaly (MSE: {mse:.6f})"}
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
# MODULE 6: API CHO DASHBOARD FRONTEND
# ==========================================
@app.get("/api/logs")
async def get_traffic_logs():
    """Lấy toàn bộ lịch sử (cả xanh lẫn đỏ) để Frontend vẽ biểu đồ"""
    logs = []
    cursor = app.mongodb["traffic_logs"].find().sort("timestamp", -1).limit(1000) # Giới hạn 1000 bản ghi mới nhất để web không bị lag
    
    async for document in cursor:
        document["_id"] = str(document["_id"]) 
        logs.append(document)
        
    return {
        "status": "success", 
        "total_requests": len(logs), 
        "data": logs
    }

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
    
    
    client_ip = request.headers.get("X-Fake-IP", request.client.host if request.client else "Unknown")
    raw_version = request.scope.get("http_version", "1.1")
    http_version = f"HTTP/{raw_version}"
    # ---------------------------------------------------------
    # 1. KIỂM TRA RATE LIMIT (CHỐNG DDOS/SPAM) TRƯỚC TIÊN
    # ---------------------------------------------------------
    if not check_rate_limit(client_ip):
        print(f"   >>>[RATE LIMIT] Đã chặn IP {client_ip} vì gửi quá {MAX_REQUESTS_PER_WINDOW} req/{RATE_LIMIT_WINDOW}s")
        
        # Ghi log loại tấn công này vào DB luôn cho xịn
        headers_dict = dict(request.headers)
        analysis_mock = {"engine": "Rate Limiter", "reason": "HTTP Flood / DoS Attempt"}
        process_time = (time.time() - start_time ) *1000
        bg_tasks.add_task(log_request_to_db, client_ip, request.method, request.url.path, http_version, headers_dict, analysis_mock, "RATE LIMIT EXCEEDED", "BLOCKED", 429, process_time)
        
        # Trả về lỗi 429 chuẩn quốc tế
        return HTMLResponse(
            content="<h1>429 Too Many Requests</h1>", 
            status_code=429
        )
    headers_dict = dict(request.headers)
    

    if not analysis_result["is_safe"]:
        print(f"   >>> ❌ [BLOCK] Reason: {analysis_result.get('reason')}")
        process_time = (time.time() - start_time) * 1000
        
        # --- NÉM VIỆC GHI LOG CHO TIẾN TRÌNH CHẠY NGẦM ---
        client_ip = request.headers.get("X-Fake-IP", request.client.host if request.client else "Unknown") #request.client.host if request.client else "Unknown IP"
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
        bg_tasks.add_task(log_request_to_db, client_ip, method, request.url.path, http_version, headers_dict, analysis_result, normalized_payload, "PASSED", response.status_code, process_time)
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=response.headers
        )
    except httpx.ConnectError:
        process_time = (time.time() - start_time) * 1000
        bg_tasks.add_task(log_request_to_db, client_ip, method, request.url.path, http_version, headers_dict, analysis_result, normalized_payload, "PASSED", 502, process_time)
        return HTMLResponse(content="<h1>502 Bad Gateway</h1><p>Target Server (Port 5001) Offline.</p>", status_code = 502)


if __name__ == "__main__":
    print("="*50)
    print(" RUNNING AI-WAF ON PORT 8000 (ASYNC MODE)...")
    print("="*50)
    uvicorn.run("main_waf:app", host="0.0.0.0", port=8000, reload=True)