import pandas as pd
import numpy as np
import joblib
import math
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
from sklearn.preprocessing import MinMaxScaler
import time

# --- HÀM TÍNH ĐỘ HỖN LOẠN (ENTROPY) ---
def calculate_entropy(s):
    if len(s) == 0:
        return 0.0
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())

# 1. Tải dữ liệu và TF-IDF
print("[*] Đang tải dữ liệu và TF-IDF...")
df = pd.read_csv("../data/csic_database_cleaned.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('')
y_true = df['Target'].values 

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])
X_matrix = X_sparse.toarray()

# 2. FEATURE ENGINEERING: Bơm thêm 3 Đặc trưng thủ công
print("[*] Đang trích xuất các Siêu đặc trưng (Length, Special Chars, Entropy)...")
# Tính toán
df['length'] = df['Full_Payload'].apply(len)
df['special_chars'] = df['Full_Payload'].apply(lambda x: sum(not c.isalnum() and not c.isspace() for c in x))
df['entropy'] = df['Full_Payload'].apply(calculate_entropy)

# Trích xuất 3 cột này ra thành ma trận phụ
custom_features = df[['length', 'special_chars', 'entropy']].values

# BẮT BUỘC: Phải chuẩn hóa (Scale) 3 cột này về khoảng (0, 1) để không làm lu mờ TF-IDF
scaler = MinMaxScaler()
custom_features_scaled = scaler.fit_transform(custom_features)

# Lưu bộ Scaler lại để Giai đoạn 3 (FastAPI) dùng
joblib.dump(scaler, "custom_features_scaler.pkl")

# HỢP THỂ: Ghép ma trận 5000 chiều (TF-IDF) với 3 chiều (Thủ công) = 5003 chiều
X_combined = np.hstack((X_matrix, custom_features_scaled))
print(f"[+] Kích thước dữ liệu mới sau khi hợp thể: {X_combined.shape}")

# 3. Xây dựng và Huấn luyện Autoencoder với Dữ liệu mới
X_normal = X_combined[y_true == 1]
print(f"[*] Số lượng request sạch dùng để huấn luyện AE: {X_normal.shape[0]}")

input_dim = X_combined.shape[1] # Bây giờ là 5003 chiều
input_layer = Input(shape=(input_dim,))
encoded = Dense(256, activation='relu')(input_layer)
encoded = Dropout(0.2)(encoded)
bottleneck = Dense(32, activation='relu')(encoded)
decoded = Dense(256, activation='relu')(bottleneck)
output_layer = Dense(input_dim, activation='sigmoid')(decoded)

autoencoder = Model(inputs=input_layer, outputs=output_layer)
autoencoder.compile(optimizer='adam', loss='mse')

print("\n[*] Đang huấn luyện Autoencoder (Feature Engineering)...")
early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
autoencoder.fit(
    X_normal, X_normal, 
    epochs=25, batch_size=256, validation_split=0.2, 
    callbacks=[early_stop], verbose=1
)

autoencoder.save("full_autoencoder_waf_fe.h5")
print("[+] Đã lưu mô hình mới vào full_autoencoder_waf_fe.h5")

# 4. Tính toán Sai số tái tạo (MSE)
print("\n[*] Đang dùng AI để vẽ lại và tính toán sai số...")
start_time = time.time()
X_predictions = autoencoder.predict(X_combined) # Dùng X_combined
mse = np.mean(np.power(X_combined - X_predictions, 2), axis=1)
print(f"[+] Tính toán xong! Thời gian: {time.time() - start_time:.2f} giây.")

# 5. Dò tìm Threshold tối ưu nhất (Dynamic Thresholding)
print("\n[*] Đang tìm Threshold tối ưu...")
best_threshold = 0
best_accuracy = 0

for percent in range(50, 100):
    thresh_candidate = np.percentile(mse[y_true == 1], percent)
    y_pred_candidate = np.where(mse > thresh_candidate, -1, 1)
    current_acc = accuracy_score(y_true, y_pred_candidate)
    
    if current_acc > best_accuracy:
        best_accuracy = current_acc
        best_threshold = thresh_candidate

print(f"\n[!] TÌM THẤY NGƯỠNG TỐI ƯU (THRESHOLD): {best_threshold:.6f}")
print(f"[!] DỰ KIẾN ACCURACY CAO NHẤT ĐẠT: {best_accuracy*100:.2f}%")

y_pred = np.where(mse > best_threshold, -1, 1)

# 6. Đánh giá và Vẽ Ma trận nhầm lẫn
print("\n" + "="*45)
print("   BÁO CÁO KẾT QUẢ: AUTOENCODER + FEATURE ENGINEERING   ")
print("="*45)

cm = confusion_matrix(y_true, y_pred)
print("\n1. MA TRẬN NHẦM LẪN:")
print(cm)
print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_true, y_pred, target_names=["Tấn công (-1)", "Bình thường (1)"]))

# Vẽ biểu đồ
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=["Tấn công (-1)", "Bình thường (1)"], 
            yticklabels=["Tấn công (-1)", "Bình thường (1)"],
            annot_kws={"size": 14})
plt.title('Ma trận nhầm lẫn - WAF Autoencoder (Feature Engineering)', fontsize=14, pad=20)
plt.ylabel('Thực tế', fontsize=12)
plt.xlabel('Dự đoán', fontsize=12)
plt.tight_layout()
plt.savefig("fe_confusion_matrix.png", dpi=300)
print("\n[+] Đã xuất ảnh Ma trận nhầm lẫn ra: fe_confusion_matrix.png")