import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from scipy.sparse import hstack
import re

# 1. Tải dữ liệu
FILE_PATH = "../data/super_waf_dataset.csv"
print("[*] Đang tải dữ liệu...")
df = pd.read_csv(FILE_PATH)

# Đảm bảo dữ liệu là chuỗi và không bị rỗng
df['Full_Payload'] = df['Full_Payload'].fillna('').astype(str)

# === BƯỚC MỚI: BÓC TÁCH METHOD VÀ PATH TỪ FULL_PAYLOAD ===
print("[*] Đang phân tích cú pháp HTTP Request...")

# Xóa dấu ngoặc kép ở đầu chuỗi (nếu có) để tách từ cho chuẩn
df['Clean_Payload'] = df['Full_Payload'].str.lstrip('"')

# Lấy phần tử đầu tiên làm Method (GET, POST, PUT...)
df['Method'] = df['Clean_Payload'].apply(lambda x: x.split()[0].upper() if len(x.split()) > 0 else 'UNKNOWN')

# Lấy phần tử thứ hai làm Path (URL / URI)
df['Path'] = df['Clean_Payload'].apply(lambda x: x.split()[1] if len(x.split()) > 1 else '/')


# === PHẦN 1: MA TRẬN TF-IDF (GIỮ SỨC MẠNH BẮT SQLi/XSS) ===
print("[*] Đang tính toán ma trận TF-IDF Char N-gram...")
vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4), max_features=5000)
tfidf_matrix = vectorizer.fit_transform(df['Full_Payload'])


# === PHẦN 2: FEATURE ENGINEERING (DẠY AI NHẬN DIỆN CẤU TRÚC) ===
print("[*] Đang trích xuất các đặc trưng nâng cao...")

# Đặc trưng 1: Có phải Method nguy hiểm thường dùng để tấn công/dò quét? (1 = Có, 0 = Không)
is_risky_method = df['Method'].isin(['POST', 'PUT', 'DELETE', 'PATCH']).astype(float).values.reshape(-1, 1)

# Đặc trưng 2: Độ dài của Path (Các tool quét thư mục thường gửi Path chứa rác rất dài)
path_length = df['Path'].apply(len).astype(float).values.reshape(-1, 1)

# Đặc trưng 3: Có chứa các từ khóa nhạy cảm của framework / hệ thống hay không?
sensitive_keywords = ['_next', 'api', 'env', 'config', 'admin', 'setup', 'xml', 'json']
has_sensitive_keyword = df['Path'].apply(
    lambda x: 1.0 if any(word in str(x).lower() for word in sensitive_keywords) else 0.0
).values.reshape(-1, 1)


# === PHẦN 3: GHÉP NỐI (STACKING) CÁC ĐẶC TRƯNG ===
print("[*] Đang ghép nối các ma trận đặc trưng...")
# Nối ma trận 5000 chiều của TF-IDF với 3 chiều đặc trưng mới
X_matrix_final = hstack([tfidf_matrix, is_risky_method, path_length, has_sensitive_keyword])

print(f"\n[+] Hoàn tất! Kích thước ma trận tính toán mới: {X_matrix_final.shape}")
print(f"    -> AI sẽ được học {X_matrix_final.shape[1]} đặc trưng (Bao gồm ngữ nghĩa ký tự + Hành vi cấu trúc).")

# 4. Lưu lại Vectorizer
joblib.dump(vectorizer, 'tfidf_waf.pkl')
print("[+] Đã lưu bộ quy tắc dịch TF-IDF vào: tfidf_waf.pkl")

# GHI CHÚ CHO BƯỚC TRAIN:
# Bạn sẽ dùng X_matrix_final và df['Target'] để đưa vào hàm train:
# rf_model.fit(X_matrix_final, df['Target'])