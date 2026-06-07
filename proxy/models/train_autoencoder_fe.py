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
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import TruncatedSVD
import time

# --- HÀM TÍNH ĐỘ HỖN LOẠN (ENTROPY) ---
def calculate_entropy(s):
    if len(s) == 0:
        return 0.0
    p, lns = Counter(s), float(len(s))
    return -sum(count/lns * math.log(count/lns, 2) for count in p.values())

# 1. Tải dữ liệu và TF-IDF
print("[*] Đang tải dữ liệu và TF-IDF...")
df = pd.read_csv("../data/super_waf_dataset.csv")
df['Full_Payload'] = df['Full_Payload'].fillna('').astype(str)
y_true = df['Target'].values 

vectorizer = joblib.load("tfidf_waf.pkl")
X_sparse = vectorizer.transform(df['Full_Payload'])
X_matrix = X_sparse.toarray()

# =====================================================================
# BƯỚC 1: GIẢM CHIỀU DỮ LIỆU TỪ 5000 XUỐNG 100 CHIỀU (SVD)
# =====================================================================
print("[*] Đang ép ma trận thưa 5000 chiều xuống còn 100 chiều (TruncatedSVD)...")
svd = TruncatedSVD(n_components=100, random_state=42)
X_svd = svd.fit_transform(X_sparse)
joblib.dump(svd, "svd_waf.pkl")
print(f"[+] Kích thước sau khi ép SVD: {X_svd.shape}")

# =====================================================================
# BƯỚC 2: FEATURE ENGINEERING (HỢP NHẤT TOÀN BỘ ĐẶC TRƯNG)
# =====================================================================
print("[*] Đang trích xuất Bộ Siêu đặc trưng (Cấu trúc + Dị thường)...")

# A. Đặc trưng cấu trúc (Kế thừa từ Random Forest)
df['Clean_Payload'] = df['Full_Payload'].str.lstrip('"')
df['Method'] = df['Clean_Payload'].apply(lambda x: x.split()[0].upper() if len(x.split()) > 0 else 'UNKNOWN')
df['Path'] = df['Clean_Payload'].apply(lambda x: x.split()[1] if len(x.split()) > 1 else '/')

df['is_risky_method'] = df['Method'].isin(['POST', 'PUT', 'DELETE', 'PATCH']).astype(float)
df['path_length'] = df['Path'].apply(len).astype(float)

sensitive_keywords = ['_next', 'api', 'env', 'config', 'admin', 'setup', 'xml', 'json']
df['has_sensitive_keyword'] = df['Path'].apply(lambda x: 1.0 if any(w in str(x).lower() for w in sensitive_keywords) else 0.0)

# B. Đặc trưng dị thường (Kế thừa từ phiên bản cũ của Autoencoder)
df['special_chars'] = df['Full_Payload'].apply(lambda x: sum(not c.isalnum() and not c.isspace() for c in x)).astype(float)
df['entropy'] = df['Full_Payload'].apply(calculate_entropy).astype(float)

# Gom 5 tính năng này lại thành ma trận
custom_features = df[['is_risky_method', 'path_length', 'has_sensitive_keyword', 'special_chars', 'entropy']].values

# CHUẨN HÓA (Scale) 5 cột này về khoảng (0, 1) để tương thích với Autoencoder
scaler = MinMaxScaler()
custom_features_scaled = scaler.fit_transform(custom_features)
joblib.dump(scaler, "custom_features_scaler.pkl")

# HỢP THỂ: Ghép ma trận 100 chiều (SVD) với 5 chiều (Thủ công) = 105 chiều
X_combined = np.hstack((X_svd, custom_features_scaled))
print(f"[+] Kích thước dữ liệu mới sau khi hợp thể: {X_combined.shape}")


# 3. Xây dựng và Huấn luyện Autoencoder
X_normal = X_combined[y_true == 0]
print(f"[*] Số lượng request sạch dùng để huấn luyện AE: {X_normal.shape[0]}")

input_dim = X_combined.shape[1]  # Lúc này là 105
input_layer = Input(shape=(input_dim,))

# Kiến trúc thắt cổ chai: 105 -> 64 -> 16 -> 64 -> 105
encoded = Dense(64, activation='relu')(input_layer)
encoded = Dropout(0.2)(encoded)
bottleneck = Dense(16, activation='relu')(encoded)
decoded = Dense(64, activation='relu')(bottleneck)
output_layer = Dense(input_dim, activation='linear')(decoded)

autoencoder = Model(inputs=input_layer, outputs=output_layer)
autoencoder.compile(optimizer='adam', loss='mse')

print("\n[*] Đang huấn luyện Autoencoder (SVD + Feature Engineering)...")
early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
autoencoder.fit(
    X_normal, X_normal, 
    epochs=25, batch_size=256, validation_split=0.2, 
    callbacks=[early_stop], verbose=1
)

autoencoder.save_weights("autoencoder.weights.h5")
print("[+] Đã lưu mô hình mới vào autoencoder.weights.h5")

# 4. Tính toán Sai số tái tạo (MSE) và Tìm Threshold
print("\n[*] Đang tìm Threshold tối ưu...")
start_time = time.time()
X_predictions = autoencoder.predict(X_combined) 
mse = np.mean(np.power(X_combined - X_predictions, 2), axis=1)

best_threshold = 0
best_accuracy = 0
for percent in range(50, 100):
    thresh_candidate = np.percentile(mse[y_true == 0], percent)
    y_pred_candidate = np.where(mse > thresh_candidate, 1, 0)
    current_acc = accuracy_score(y_true, y_pred_candidate)
    
    if current_acc > best_accuracy:
        best_accuracy = current_acc
        best_threshold = thresh_candidate

print(f"\n[!] TÌM THẤY NGƯỠNG TỐI ƯU (THRESHOLD): {best_threshold:.6f}")
print(f"[!] DỰ KIẾN ACCURACY CAO NHẤT ĐẠT: {best_accuracy*100:.2f}%")

y_pred = np.where(mse > best_threshold, 1, 0)

# 6. Đánh giá 
print("\n" + "="*45)
print("   BÁO CÁO KẾT QUẢ: SVD AUTOENCODER   ")
print("="*45)
cm = confusion_matrix(y_true, y_pred)
print("\n1. MA TRẬN NHẦM LẪN:")
print(cm)
print("\n2. CÁC CHỈ SỐ CHI TIẾT:")
print(classification_report(y_true, y_pred, target_names=["Normal (0)", "Attack (1)"]))

# Vẽ biểu đồ
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=["Normal (0)", "Attack (1)"], 
            yticklabels=["Normal (0)", "Attack (1)"], 
            annot_kws={"size": 14})
plt.title('Confusion Matrix - SVD Autoencoder (105 Dims)', fontsize=14, pad=20)
plt.ylabel('True Label', fontsize=12)
plt.xlabel('Predict Label', fontsize=12)
plt.tight_layout()
plt.savefig("fe_confusion_matrix_ae_final.png", dpi=300)
print("\n[+] Đã xuất ảnh Ma trận nhầm lẫn ra: fe_confusion_matrix_ae.png")