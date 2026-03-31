import joblib
import numpy as np
from tensorflow.keras.models import load_model
import math
from collections import Counter
import warnings
warnings.filterwarnings('ignore') # Tắt cảnh báo

# --- HÀM TÍNH ENTROPY ---
def calculate_entropy(s):
    if len(s) == 0:
        return 0.0
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())

print("[*] Đang khởi động hệ thống Tường lửa Dual-Engine...")
vectorizer = joblib.load("tfidf_waf.pkl")
rf_model = joblib.load("random_forest_waf.pkl")
autoencoder = load_model("full_autoencoder_waf_fe.h5", compile=False)
scaler = joblib.load("custom_features_scaler.pkl") # Tải bộ chuẩn hóa 3 đặc trưng

AE_THRESHOLD = 0.000062 # Điền ngưỡng của bạn vào đây

def scan_http_request(raw_payload):
    print(f"\n[+] Đang quét Payload:\n{raw_payload.strip()[:80]}...") 
    
    # BƯỚC A1: Dữ liệu 5000 chiều cho Random Forest
    vector = vectorizer.transform([raw_payload])
    dense_vector = vector.toarray()
    
    # BƯỚC A2: Chuẩn bị thêm 3 chiều cho Autoencoder
    length = len(raw_payload)
    special_chars = sum(not c.isalnum() and not c.isspace() for c in raw_payload)
    entropy = calculate_entropy(raw_payload)
    
    # Phải đi qua Scaler để ép về khoảng (0, 1) giống lúc train
    custom_features = np.array([[length, special_chars, entropy]])
    scaled_features = scaler.transform(custom_features)
    
    # Hợp thể: 5000 + 3 = 5003 chiều
    ae_input = np.hstack((dense_vector, scaled_features))

    # BƯỚC B: Màng lọc 1 (Random Forest - Ăn 5000 chiều)
    rf_classes = list(rf_model.classes_)
    normal_index = rf_classes.index(1) 
    
    rf_probs = rf_model.predict_proba(vector)[0]
    normal_prob = rf_probs[normal_index] * 100
    
    print(f"   -> [RF Score] Điểm an toàn: {normal_prob:.2f}%")
    
    if normal_prob >= 80.0:
        return "✅ CHO QUA (Màng lọc 1 tin tưởng tuyệt đối!)"
    elif normal_prob <= 30.0:
        return "❌ CHẶN LẠI (Màng lọc 1 nhận diện mã độc đã biết!)"
    else:
        print("   -> [!] Màng lọc 1 lưỡng lự, chuyển giao cho Autoencoder...")
        
        # BƯỚC C: Màng lọc 2 (Autoencoder - Ăn 5003 chiều)
        ae_reconstruction = autoencoder.predict(ae_input, verbose=0)
        mse = np.mean(np.power(ae_input - ae_reconstruction, 2))
        
        print(f"   -> [AE Score] MSE: {mse:.6f} / Ngưỡng: {AE_THRESHOLD}")
        if mse > AE_THRESHOLD:
            return "❌ CHẶN LẠI (Autoencoder bắt được Zero-day!)"
        else:
            return "✅ CHO QUA (Autoencoder xác nhận an toàn)"

if __name__ == "__main__":
    print("="*60)
    
    # Test 1: Người dùng bình thường
    req_normal = """GET http://localhost:8080/tienda1/global/estilos.css HTTP/1.1"""
    print(scan_http_request(req_normal))
    
    # Test 2: Hacker SQL Injection (Đã biết)
    req_sqli = """GET http://localhost:8080/tienda1/publico/carrito.jsp/.BAK HTTP/1.1

username=admin' OR 1=1--&password=123"""
    print(scan_http_request(req_sqli))
    
    # Test 3: Hacker XSS (Mã độc ngụy trang)
    req_xss = """GET /tienda1/publico/articulos.jsp?id=<script>alert(1)</script> HTTP/1.1
Host: localhost:8080"""
    print(scan_http_request(req_xss))