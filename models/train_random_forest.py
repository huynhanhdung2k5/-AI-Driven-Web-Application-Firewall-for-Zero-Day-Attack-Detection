import pandas as pd
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import time

# 1. Tải dữ liệu và Bộ từ vựng (Vectorizer) đã lưu
print("[*] Đang tải dữ liệu và TF-IDF...")
df = pd.read_csv("../data/csic_database_cleaned.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('')
y_true = df['Target'] 

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])

# 2. CHIA TẬP DỮ LIỆU (Train/Test Split)
# Chia dữ liệu thành 80% để học (Train) và 20% để thi (Test)
print("[*] Đang chia tập dữ liệu (80% Train, 20% Test)...")
X_train, X_test, y_train, y_test = train_test_split(X_sparse, y_true, test_size=0.2, random_state=42)

# 3. Khởi tạo và Huấn luyện Rừng ngẫu nhiên (Random Forest)
print(f"[*] Đang huấn luyện Random Forest trên {X_train.shape[0]} request (Mất khoảng vài chục giây)...")
start_time = time.time()

# Dùng 100 cây quyết định, chạy trên toàn bộ nhân CPU (n_jobs=-1)
rf_model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)

print(f"[+] Huấn luyện xong! Thời gian: {time.time() - start_time:.2f} giây.")

# 4. Làm bài thi đánh giá mô hình (trên tập 20% Test)
print("\n[*] Đang làm bài thi đánh giá mô hình Màng lọc 1...")
y_pred = rf_model.predict(X_test)

print("\n" + "="*45)
print("     BÁO CÁO KẾT QUẢ: RANDOM FOREST (MÀNG LỌC 1)     ")
print("="*45)

# Lấy dữ liệu ma trận
cm = confusion_matrix(y_test, y_pred)

print("\n1. MA TRẬN NHẦM LẪN (Terminal):")
print(cm)

print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_test, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))

# 5. CHỈNH SỬA: Vẽ và Lưu Ma trận nhầm lẫn (Confusion Matrix) ra file ảnh
print("\n[*] Đang vẽ Ma trận nhầm lẫn chuyên nghiệp cho báo cáo...")

# Định nghĩa nhãn cho các trục dựa trên mapping Target
# sklearn's classification_report sorts labels, assuming [attack_label, normal_label]
# typically map attack=1, normal=0 or similar binary. Standard assumes 0=Normal, 1=Attack.
# Looking at classification_report output names provided previously: ['Attack', 'Normal']
class_names = ["Tấn công (-1)", "Bình thường (1)"] 

plt.figure(figsize=(8, 6))

# Dùng Heatmap của Seaborn để tô màu. fmt='d' để hiện số nguyên, cmap='Blues' cho tông màu chuyên nghiệp
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=class_names, 
            yticklabels=class_names,
            annot_kws={"size": 14}) # Phóng to font chữ số liệu

plt.title('Ma trận nhầm lẫn (Confusion Matrix) - WAF Random Forest', fontsize=16, pad=20)
plt.ylabel('Thực tế (True Label)', fontsize=12)
plt.xlabel('Dự đoán (Predicted Label)', fontsize=12)

# Căn chỉnh lề tự động cho đẹp
plt.tight_layout()

# Lưu thành file ảnh chất lượng cao (300 dpi cực kỳ nét khi đưa vào Word/Slide)
plt.savefig("rf_confusion_matrix.png", dpi=300)
print("[+] Đã xuất ảnh Ma trận nhầm lẫn ra file: rf_confusion_matrix.png")


# 6. Trích xuất top 20 Từ khóa nguy hiểm nhất (Feature Importances)
print("\n[*] Đang phân tích mức độ nguy hiểm của các từ khóa...")
importances = rf_model.feature_importances_
feature_names = vectorizer.get_feature_names_out()

feature_importance_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False).head(20)

plt.figure(figsize=(10, 8))
sns.barplot(x='Importance', y='Feature', data=feature_importance_df, palette='Reds_r')
plt.title('Top 20 Từ khóa/Đặc trưng quyết định Mã Độc (Random Forest WAF)', fontsize=14)
plt.tight_layout()
plt.savefig("rf_feature_importances.png", dpi=300)
print("[+] Đã xuất biểu đồ giải thích AI ra file: rf_feature_importances.png")

# 7. Xuất chuồng (Export Model)
joblib.dump(rf_model, "random_forest_waf.pkl")
print("\n[+] Đã đóng gói Màng lọc 1 vào: random_forest_waf.pkl")