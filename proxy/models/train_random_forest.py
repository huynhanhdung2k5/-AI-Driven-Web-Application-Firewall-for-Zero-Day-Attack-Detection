import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from scipy.sparse import hstack # Import thư viện để ghép nối ma trận
import time

# 1. Tải dữ liệu và Bộ từ vựng (Vectorizer) đã lưu
print("[*] Đang tải dữ liệu và TF-IDF...")
df = pd.read_csv("../data/super_waf_dataset.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('').astype(str)
y_true = df['Target'] 

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])

# === BƯỚC NÂNG CẤP: TRÍCH XUẤT VÀ GHÉP NỐI ĐẶC TRƯNG CẤU TRÚC ===
print("[*] Đang trích xuất và ghép nối các đặc trưng nâng cao...")

# Bóc tách Method và Path
df['Clean_Payload'] = df['Full_Payload'].str.lstrip('"')
df['Method'] = df['Clean_Payload'].apply(lambda x: x.split()[0].upper() if len(x.split()) > 0 else 'UNKNOWN')
df['Path'] = df['Clean_Payload'].apply(lambda x: x.split()[1] if len(x.split()) > 1 else '/')

# Tạo 3 tính năng mới
is_risky_method = df['Method'].isin(['POST', 'PUT', 'DELETE', 'PATCH']).astype(float).values.reshape(-1, 1)
path_length = df['Path'].apply(len).astype(float).values.reshape(-1, 1)

sensitive_keywords = ['_next', 'api', 'env', 'config', 'admin', 'setup', 'xml', 'json']
has_sensitive_keyword = df['Path'].apply(
    lambda x: 1.0 if any(word in str(x).lower() for word in sensitive_keywords) else 0.0
).values.reshape(-1, 1)

# Ghép nối thành ma trận tổng hợp
X_combined = hstack([X_sparse, is_risky_method, path_length, has_sensitive_keyword])


# 2. CHIA TẬP DỮ LIỆU (Train/Test Split)
# Thay X_sparse bằng X_combined
print("[*] Đang chia tập dữ liệu (80% Train, 20% Test)...")
X_train, X_test, y_train, y_test = train_test_split(X_combined, y_true, test_size=0.2, random_state=42)


# 3. Khởi tạo và Huấn luyện Rừng ngẫu nhiên (Random Forest)
print(f"[*] Đang huấn luyện Random Forest trên {X_train.shape[0]} request (Mất khoảng vài chục giây)...")
start_time = time.time()

rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

print(f"[+] Huấn luyện xong! Thời gian: {time.time() - start_time:.2f} giây.")


# 4. Làm bài thi đánh giá mô hình
print("\n[*] Đang làm bài thi đánh giá mô hình Màng lọc 1...")
y_pred = rf_model.predict(X_test)

print("\n" + "="*45)
print("     BÁO CÁO KẾT QUẢ: RANDOM FOREST (MÀNG LỌC 1)     ")
print("="*45)

cm = confusion_matrix(y_test, y_pred)
print("\n1. MA TRẬN NHẦM LẪN (Terminal):")
print(cm)
print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_test, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))


# 5. CHỈNH SỬA: Vẽ và Lưu Ma trận nhầm lẫn
print("\n[*] Đang vẽ Ma trận nhầm lẫn chuyên nghiệp cho báo cáo...")
class_names = ["Attack (1)", "Normal (0)"] 
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=class_names, 
            yticklabels=class_names,
            annot_kws={"size": 14})
plt.title('Confusion Matrix - WAF Random Forest', fontsize=16, pad=20)
plt.ylabel('True Label', fontsize=12)
plt.xlabel('Predicted Label', fontsize=12)
plt.tight_layout()
plt.savefig("rf_confusion_matrix.png", dpi=300)
print("[+] Đã xuất ảnh Ma trận nhầm lẫn ra file: rf_confusion_matrix.png")


# 6. Trích xuất top 20 Từ khóa nguy hiểm nhất (ĐÃ SỬA LỖI ĐỒNG BỘ CHIỀU)
print("\n[*] Đang phân tích mức độ nguy hiểm của các tính năng...")
importances = rf_model.feature_importances_

# Lấy tên từ khóa của TF-IDF và NỐI THÊM 3 tên của tính năng cấu trúc
tfidf_feature_names = vectorizer.get_feature_names_out()
structural_feature_names = ['is_risky_method', 'path_length', 'has_sensitive_keyword']
all_feature_names = np.append(tfidf_feature_names, structural_feature_names)

feature_importance_df = pd.DataFrame({'Feature': all_feature_names, 'Importance': importances})
feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False).head(20)

plt.figure(figsize=(10, 8))
sns.barplot(x='Importance', y='Feature', data=feature_importance_df, palette='Reds_r')
plt.title('Top 20 Features decide anomalous (Random Forest WAF)', fontsize=14)
plt.tight_layout()
plt.savefig("rf_feature_importances.png", dpi=300)
print("[+] Đã xuất biểu đồ giải thích AI ra file: rf_feature_importances.png")


# 7. Xuất chuồng (Export Model)
joblib.dump(rf_model, "random_forest_waf.pkl")
print("\n[+] Đã đóng gói Màng lọc 1 vào: random_forest_waf.pkl")