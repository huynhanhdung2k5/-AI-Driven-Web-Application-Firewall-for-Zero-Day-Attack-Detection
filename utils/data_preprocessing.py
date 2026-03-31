import pandas as pd

# 1. Tải dữ liệu thô
FILE_PATH = "data/csic_database.csv" # Sửa lại tên file nếu cần
print("[*] Đang tải dữ liệu thô...")
df = pd.read_csv(FILE_PATH)

print(f"Kích thước ban đầu: {df.shape}")

# 2. Đổi tên cột cho chuẩn xác
# Cột 'Unnamed: 0' thực chất là nhãn (Label), cột 'lenght' bị sai chính tả
df.rename(columns={'Unnamed: 0': 'Label', 'lenght': 'length'}, inplace=True)

# 3. Loại bỏ các "Cột rác" (Noise Reduction)
# Đây là các header chuẩn của trình duyệt, hacker ít khi chèn mã độc vào đây
# Việc xóa chúng giúp model train nhanh hơn và đỡ bị nhiễu
columns_to_drop = [
    'Pragma', 'Cache-Control', 'Accept', 'Accept-encoding', 
    'Accept-charset', 'language', 'connection', 'classification'
]
df.drop(columns=columns_to_drop, inplace=True, errors='ignore')

# 4. Xử lý giá trị rỗng (NaN)
# Tránh lỗi khi ghép chuỗi văn bản
df.fillna('', inplace=True)

# 5. Kỹ thuật Hợp nhất đặc trưng (Feature Concatenation)
# Gộp Method, URL và Request Body (content) thành một "câu văn" hoàn chỉnh.
# Ví dụ: "GET http://localhost:8080/login?id=1 <script>alert(1)</script>"
df['Full_Payload'] = df['Method'] + " " + df['URL'] + " " + df['content']

# 6. Gán nhãn cho Isolation Forest (Target Encoding)
# Isolation Forest quy định: Bình thường (Inliers) = 1, Bất thường (Outliers/Zero-day) = -1
df['Target'] = df['Label'].apply(lambda x: 1 if str(x).strip().lower() == 'normal' else -1)

print("\n--- 5 DÒNG PAYLOAD ĐÃ GỘP ---")
pd.set_option('display.max_colwidth', 80) # Mở rộng hiển thị text
print(df[['Label', 'Target', 'Full_Payload']].head())

# 7. Lưu kết quả ra file mới để Tuần 3 và Tuần 4 sử dụng
CLEANED_FILE = "data/csic_database_cleaned.csv"
df.to_csv(CLEANED_FILE, index=False)
print(f"\n[+] Đã lưu dữ liệu siêu sạch vào: {CLEANED_FILE}")