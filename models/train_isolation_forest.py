import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix
import time

# 1. Tải dữ liệu và Bộ từ vựng (Vectorizer)
print("[*] Đang tải dữ liệu và bộ từ vựng TF-IDF...")
df = pd.read_csv("../data/csic_database_cleaned.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('')

# Lấy nhãn thực tế để lát nữa chấm điểm AI (1: Bình thường, -1: Tấn công)
y_true = df['Target'] 

# Load lại file .pkl bạn vừa tạo ban nãy
vectorizer = joblib.load("tfidf_waf.pkl")

# Biến văn bản thành ma trận
X_matrix = vectorizer.transform(df['Full_Payload'])

# 2. Khởi tạo Mô hình Isolation Forest
print("[*] Bắt đầu huấn luyện AI (Quá trình này có thể mất 1-2 phút)...")
start_time = time.time()

# Tham số contamination: Ước lượng tỷ lệ request độc hại trong dataset (Khoảng 41% đối với CSIC 2010)
# Tham số n_estimators: Số lượng "cây" trong rừng (100 là mức chuẩn để cân bằng tốc độ và độ chính xác)
iso_forest = IsolationForest(n_estimators=100, contamination=0.41, random_state=42, n_jobs=-1)

# AI bắt đầu "Học"
iso_forest.fit(X_matrix)

train_time = time.time() - start_time
print(f"[+] Huấn luyện xong! Thời gian: {train_time:.2f} giây.")

# 3. Làm bài thi (Đánh giá hiệu năng)
print("\n[*] Đang làm bài thi đánh giá (Predict)...")
y_pred = iso_forest.predict(X_matrix)

print("\n" + "="*40)
print("     BÁO CÁO KẾT QUẢ ĐÁNH GIÁ (TUẦN 5)     ")
print("="*40)
print("\n1. MA TRẬN NHẦM LẪN (Confusion Matrix):")
# Hiện thị dưới dạng: 
# [Bắt đúng mã độc (True Neg)  |  Bắt nhầm người thường (False Pos)]
# [Bỏ lọt mã độc (False Neg)   |  Cho qua đúng người thường (True Pos)]
print(confusion_matrix(y_true, y_pred))

print("\n2. CÁC CHỈ SỐ CHI TIẾT (Precision, Recall, F1-Score):")
print(classification_report(y_true, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))

# 4. Xuất chuồng (Export Model)
MODEL_PATH = "isolation_forest_waf.pkl"
joblib.dump(iso_forest, MODEL_PATH)
print(f"\n[+] Đã đóng gói bộ não AI thành công vào: {MODEL_PATH}")