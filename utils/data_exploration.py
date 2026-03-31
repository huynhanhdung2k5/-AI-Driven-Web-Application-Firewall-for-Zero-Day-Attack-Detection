import pandas as pd

# TODO: Đổi tên file này thành đúng tên file CSV bạn vừa tải về
FILE_PATH = "data/csic_database.csv" 

print("[*] Đang tải dữ liệu từ bộ dataset...")
df = pd.read_csv(FILE_PATH)

print("\n--- TỔNG QUAN DỮ LIỆU ---")
print(f"Tổng số HTTP Request: {len(df)} dòng")
print(f"Số lượng cột (đặc trưng): {len(df.columns)} cột")

print("\n--- TÊN CÁC CỘT TRONG DATASET ---")
print(df.columns.tolist())

print("\n--- 5 DÒNG DỮ LIỆU ĐẦU TIÊN ---")
# Chỉ hiển thị một số cột quan trọng để dễ nhìn (bạn có thể chỉnh sửa tên cột nếu Kaggle đặt tên khác)
# Ví dụ: 'Method', 'URL', 'User-Agent', 'Label'
print(df.head())