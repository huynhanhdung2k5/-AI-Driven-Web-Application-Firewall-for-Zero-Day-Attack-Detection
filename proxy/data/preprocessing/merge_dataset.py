import pandas as pd

print("[*] Đang đọc 3 bộ dữ liệu chiến lược...")
# 1. Bộ CSIC (Kinh điển) - CẮM THÊM BỘ LỌC NHÃN Ở ĐÂY
df_csic = pd.read_csv("../data/csic_database_cleaned.csv")[['Full_Payload', 'Target']]
# Phiên dịch nhãn: 1 (An toàn cũ) -> 0 (An toàn mới) | -1 (Mã độc cũ) -> 1 (Mã độc mới)
df_csic['Target'] = df_csic['Target'].replace({1: 0, -1: 1})

# 2. Bộ FWAF (Đã cân bằng 50:50) - Giữ nguyên vì đã chuẩn (0: An toàn, 1: Mã độc)
df_fwaf = pd.read_csv("balanced_fwaf_dataset.csv")

# 3. Bộ SecLists (Fuzzing dị biệt) - Giữ nguyên vì đã chuẩn (1: Mã độc)
df_seclists = pd.read_csv("seclists_malicious_update.csv")

print("[*] Đang hợp thể thành Super Dataset...")
df_super = pd.concat([df_csic, df_fwaf, df_seclists], ignore_index=True)

# Xáo trộn toàn bộ (Shuffle) cực kỳ quan trọng
df_super = df_super.sample(frac=1, random_state=42).reset_index(drop=True)

# Loại bỏ các request trùng lặp hoàn toàn
df_super = df_super.drop_duplicates()

output_name = "super_waf_dataset.csv"
df_super.to_csv(output_name, index=False)

print("\n[*] ĐÃ GỘP XONG VÀ ĐỒNG NHẤT NHÃN THÀNH CÔNG!")
print(f"[*] Tổng số lượng dữ liệu sẵn sàng train: {len(df_super)} dòng.")
print(f"[*] Số lượng - An toàn (0): {len(df_super[df_super['Target']==0])} | Mã độc (1): {len(df_super[df_super['Target']==1])}")