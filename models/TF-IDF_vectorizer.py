import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
import os


# 1. Tải dữ liệu siêu sạch từ bước trước
FILE_PATH = "../data/csic_database_cleaned.csv"
print("[*] Đang tải dữ liệu...")
df = pd.read_csv(FILE_PATH)

# Đảm bảo không có dòng rỗng nào gây lỗi
df['Full_Payload'] = df['Full_Payload'].fillna('')

# 2. Khởi tạo thuật toán TF-IDF
# Giới hạn 5000 đặc trưng (từ vựng) quan trọng nhất để AI chạy nhanh nhất trong môi trường Real-time
print("[*] Đang học từ vựng và bóc tách đặc trưng (TF-IDF)...")
vectorizer = TfidfVectorizer(max_features=5000)

# 3. Ép kiểu văn bản thành Ma trận số học (Toán học hóa)
print("[*] Đang dịch văn bản sang ma trận số (việc này có thể mất vài giây)...")
X_matrix = vectorizer.fit_transform(df['Full_Payload'])

print(f"\n[+] Hoàn tất! Kích thước ma trận tính toán: {X_matrix.shape}")
print(f"    -> Ý nghĩa: {X_matrix.shape[0]} HTTP request đã được biến thành {X_matrix.shape[0]} vector.")
print(f"    -> Mỗi request giờ đây có {X_matrix.shape[1]} chiều.")

# 4. BƯỚC CỰC KỲ QUAN TRỌNG: Lưu lại "Bộ não từ vựng"
joblib.dump(vectorizer, 'tfidf_waf.pkl')
print("[+] Đã lưu bộ quy tắc dịch TF-IDF vào: models/tfidf_waf.pkl")