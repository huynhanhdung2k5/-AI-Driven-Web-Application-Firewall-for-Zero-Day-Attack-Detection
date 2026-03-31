import pandas as pd
import joblib
from tensorflow.keras.models import load_model
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix
import time

# 1. Tải dữ liệu và TF-IDF
print("[*] Đang tải dữ liệu...")
df = pd.read_csv("../data/csic_database_cleaned.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('')
y_true = df['Target']

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])
X_matrix = X_sparse.toarray()

# 2. BƯỚC ĐỘT PHÁ: Dùng Autoencoder ép 5000 chiều xuống 64 chiều
print("[*] Đang dùng Autoencoder nén dữ liệu...")
# Tham số compile=False vì ta chỉ dùng để nén (Inference), không train thêm nữa
encoder = load_model("ae_encoder.h5", compile=False) 
X_encoded = encoder.predict(X_matrix) 

# 3. Mớm 64 chiều tinh khiết này cho Isolation Forest
print(f"[*] Đang huấn luyện Isolation Forest với dữ liệu kích thước siêu gọn: {X_encoded.shape}...")
start_time = time.time()

# Vẫn giữ tỷ lệ mã độc 0.41, nhưng dữ liệu giờ đã sạch hơn nhiều
iso_forest = IsolationForest(n_estimators=200, contamination=0.41, random_state=42, n_jobs=-1)
iso_forest.fit(X_encoded)

print(f"[+] Huấn luyện xong! Thời gian: {time.time() - start_time:.2f} giây.")

# 4. Đánh giá sự lột xác
print("\n[*] Đang làm bài thi đánh giá mô hình Hybrid...")
y_pred = iso_forest.predict(X_encoded)

print("\n" + "="*45)
print("   BÁO CÁO KẾT QUẢ: AUTOENCODER + ISOLATION FOREST   ")
print("="*45)
print("\n1. MA TRẬN NHẦM LẪN:")
print(confusion_matrix(y_true, y_pred))

print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_true, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))

# 5. Lưu bộ não chiến binh này lại
joblib.dump(iso_forest, "hybrid_if_waf.pkl")
print("\n[+] Đã lưu mô hình Hybrid AI vào: models/hybrid_if_waf.pkl")