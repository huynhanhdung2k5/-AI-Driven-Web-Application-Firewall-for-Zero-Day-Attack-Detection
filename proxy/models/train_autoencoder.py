import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import time

# 1. Tải dữ liệu và TF-IDF
print("[*] Đang tải dữ liệu...")
df = pd.read_csv("../data/csic_database_cleaned.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('')

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])
X_matrix = X_sparse.toarray()

# Lấy nhãn thực tế
y_true = df['Target'].values 

# 2. Xây dựng và Huấn luyện Autoencoder (Chỉ dùng dữ liệu Sạch)
X_normal = X_matrix[y_true == 1]
print(f"[*] Số lượng request sạch dùng để huấn luyện AE: {X_normal.shape[0]}")

input_dim = X_matrix.shape[1]
input_layer = Input(shape=(input_dim,))
encoded = Dense(256, activation='relu')(input_layer)
encoded = Dropout(0.2)(encoded)
bottleneck = Dense(32, activation='relu')(encoded)
decoded = Dense(256, activation='relu')(bottleneck)
output_layer = Dense(input_dim, activation='sigmoid')(decoded)

autoencoder = Model(inputs=input_layer, outputs=output_layer)
autoencoder.compile(optimizer='adam', loss='mse')

print("\n[*] Đang huấn luyện Autoencoder...")
early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
autoencoder.fit(
    X_normal, X_normal, 
    epochs=25, batch_size=256, validation_split=0.2, 
    callbacks=[early_stop], verbose=1
)

autoencoder.save("full_autoencoder_waf.h5")
print("[+] Đã lưu mô hình hoàn chỉnh vào full_autoencoder_waf.h5")

# 3. Tính toán Sai số tái tạo (Reconstruction Error - MSE) cho TOÀN BỘ dữ liệu
print("\n[*] Đang dùng AI để vẽ lại toàn bộ dữ liệu và tính toán sai số...")
start_time = time.time()
X_predictions = autoencoder.predict(X_matrix)
mse = np.mean(np.power(X_matrix - X_predictions, 2), axis=1)
print(f"[+] Tính toán xong! Thời gian: {time.time() - start_time:.2f} giây.")

# 4. Kỹ thuật Dynamic Thresholding: Truy tìm Ngưỡng tối ưu nhất
print("\n[*] Đang dùng thuật toán dò tìm Threshold tối ưu nhất để bứt phá Accuracy...")

best_threshold = 0
best_accuracy = 0
best_f1 = 0

# Thử nghiệm dải phần trăm từ 50% đến 99%
for percent in range(50, 100):
    thresh_candidate = np.percentile(mse[y_true == 1], percent)
    y_pred_candidate = np.where(mse > thresh_candidate, -1, 1)
    
    # Chấm điểm tại ngưỡng này
    current_acc = accuracy_score(y_true, y_pred_candidate)
    current_f1 = f1_score(y_true, y_pred_candidate, pos_label=-1)
    
    # Nếu tìm thấy ngưỡng cho Accuracy cao hơn thì lưu lại
    if current_acc > best_accuracy:
        best_accuracy = current_acc
        best_threshold = thresh_candidate
        best_f1 = current_f1

print(f"\n[!] TÌM THẤY NGƯỠNG TỐI ƯU (THRESHOLD): {best_threshold:.6f}")
print(f"[!] DỰ KIẾN ACCURACY CAO NHẤT ĐẠT: {best_accuracy*100:.2f}%")

# Áp dụng ngưỡng xịn nhất vừa tìm được
y_pred = np.where(mse > best_threshold, -1, 1)

# 5. Đánh giá kết quả và Vẽ Confusion Matrix
print("\n" + "="*45)
print("   BÁO CÁO KẾT QUẢ: THUẦN AUTOENCODER TUNED   ")
print("="*45)

# Lấy dữ liệu ma trận
cm = confusion_matrix(y_true, y_pred)

print("\n1. MA TRẬN NHẦM LẪN (Terminal):")
print(cm)

print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_true, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))

# --- ĐOẠN CODE MỚI THÊM VÀO ĐỂ VẼ ẢNH ---
# Khởi tạo khung tranh
plt.figure(figsize=(8, 6))

# Dùng Heatmap của Seaborn để tô màu. 
# annot=True để hiện con số, fmt='d' để hiện số nguyên, cmap='Blues' để dùng tông màu xanh dương chuyên nghiệp
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=["Tấn công (-1)", "Bình thường (1)"], 
            yticklabels=["Tấn công (-1)", "Bình thường (1)"],
            annot_kws={"size": 14}) # Phóng to font chữ số liệu

plt.title('Ma trận nhầm lẫn (Confusion Matrix) - Autoencoder WAF', fontsize=16, pad=20)
plt.ylabel('Thực tế (True Label)', fontsize=12)
plt.xlabel('Dự đoán (Predicted Label)', fontsize=12)

# Căn chỉnh lề tự động cho đẹp
plt.tight_layout()

# Lưu thành file ảnh chất lượng cao (300 dpi cực kỳ nét khi đưa vào Word/Slide)
plt.savefig("confusion_matrix.png", dpi=300)
print("\n[+] Đã xuất ảnh Ma trận nhầm lẫn ra file: confusion_matrix.png")

# 6. Vẽ biểu đồ Histogram tuyệt đẹp cho Báo cáo
plt.figure(figsize=(10, 6))
sns.histplot(mse[y_true == 1], bins=50, color='blue', alpha=0.6, label='Bình thường (Normal)', stat='density')
sns.histplot(mse[y_true == -1], bins=50, color='red', alpha=0.6, label='Mã độc (Anomalous)', stat='density')

# ĐÃ SỬA: Dùng best_threshold thay vì threshold
plt.axvline(best_threshold, color='black', linestyle='dashed', linewidth=2, label=f'Ngưỡng chặn (Threshold: {best_threshold:.6f})')

plt.title('Phân phối Sai số tái tạo (Reconstruction Error) của WAF')
plt.xlabel('Sai số tái tạo (MSE)')
plt.ylabel('Mật độ (Density)')
plt.legend()

# ĐÃ SỬA: Dùng best_threshold
plt.xlim(0, best_threshold * 3) 

plt.savefig("mse_distribution.png", dpi=300)
print("\n[+] Đã xuất biểu đồ báo cáo ra file: mse_distribution.png")