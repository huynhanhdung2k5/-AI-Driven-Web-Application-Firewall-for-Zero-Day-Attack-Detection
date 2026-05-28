import pandas as pd
from sklearn.utils import resample

def balance_dataset():
    print("[*] Đang nạp bộ dữ liệu FWAF khổng lồ (vui lòng đợi vài giây)...")
    try:
        # Đọc file dữ liệu thô bạn vừa cào về
        df = pd.read_csv("fwaf_dataset_ready.csv")
    except FileNotFoundError:
        print("[!] Không tìm thấy file fwaf_dataset_ready.csv. Hãy kiểm tra lại tên file!")
        return

    # 1. Tách riêng 2 phe: An toàn (0) và Mã độc (1)
    df_good = df[df['Target'] == 0]
    df_bad = df[df['Target'] == 1]

    print(f"[*] Thống kê ban đầu: An toàn: {len(df_good)} | Mã độc: {len(df_bad)}")
    print("[*] Đang tiến hành Undersampling (Cắt gọt dữ liệu)...")

    # 2. Rút trích ngẫu nhiên nhóm An toàn sao cho bằng đúng nhóm Mã độc
    df_good_downsampled = resample(
        df_good,
        replace=False,          # Bốc ra là không bỏ lại (không trùng lặp)
        n_samples=len(df_bad),  # Lấy số lượng bằng đúng phe Mã độc
        random_state=42         # Chốt seed để lần nào chạy kết quả cũng giống nhau
    )

    # 3. Hợp thể 2 phe lại thành một bộ dữ liệu hoàn chỉnh
    df_balanced = pd.concat([df_good_downsampled, df_bad])

    # 4. Xáo trộn dữ liệu (Shuffle) - RẤT QUAN TRỌNG!
    # Nếu không xáo trộn, AI sẽ học hết 44k dòng an toàn rồi mới học 44k dòng mã độc -> Dễ bị tẩu hỏa nhập ma
    df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

    print("\n[*] TUYỆT VỜI! Bộ dữ liệu đã đạt 'Tỷ lệ vàng' 50:50.")
    print(f"[*] Thống kê mới: An toàn: {len(df_balanced[df_balanced['Target']==0])} | Mã độc: {len(df_balanced[df_balanced['Target']==1])}")
    print(f"[*] Tổng cộng: {len(df_balanced)} requests tinh túy nhất.")

    # 5. Xuất xưởng
    output_file = "balanced_fwaf_dataset.csv"
    df_balanced.to_csv(output_file, index=False)
    print(f"[*] Đã lưu bộ dữ liệu huấn luyện hoàn hảo vào: {output_file}")

if __name__ == "__main__":
    balance_dataset()