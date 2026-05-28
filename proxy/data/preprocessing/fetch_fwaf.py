import requests
import pandas as pd

def fetch_fwaf_dataset():
    print("[*] Đang kết nối tới Github Repository: faizann24/Fwaf...")
    
    # Link Raw trực tiếp tới các file txt trên Github
    GOOD_URL = "https://raw.githubusercontent.com/faizann24/Fwaf-Machine-Learning-driven-Web-Application-Firewall/master/goodqueries.txt"
    BAD_URL = "https://raw.githubusercontent.com/faizann24/Fwaf-Machine-Learning-driven-Web-Application-Firewall/master/badqueries.txt"
    
    dataset = []

    # 1. Tải và xử lý Good Queries (Target = 0)
    print(" -> Đang tải Good Queries (Dữ liệu sạch)...")
    resp_good = requests.get(GOOD_URL)
    if resp_good.status_code == 200:
        good_lines = resp_good.text.split('\n')
        for line in good_lines:
            payload = line.strip()
            if payload:
                # Bọc lại thành format GET request để mô hình dễ học
                dataset.append({"Full_Payload": f"GET {payload} HTTP/1.1", "Target": 0})
    else:
        print("[!] Lỗi tải Good Queries")

    # 2. Tải và xử lý Bad Queries (Target = 1)
    print(" -> Đang tải Bad Queries (Dữ liệu mã độc)...")
    resp_bad = requests.get(BAD_URL)
    if resp_bad.status_code == 200:
        bad_lines = resp_bad.text.split('\n')
        for line in bad_lines:
            payload = line.strip()
            if payload:
                dataset.append({"Full_Payload": f"GET {payload} HTTP/1.1", "Target": 1})
    else:
        print("[!] Lỗi tải Bad Queries")

    # 3. Đóng gói và lưu File
    df = pd.DataFrame(dataset)
    df = df.drop_duplicates()
    
    output_file = "fwaf_dataset_ready.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n[*] TUYỆT VỜI! Đã cào thành công {len(df)} dòng dữ liệu!")
    print(f"[*] Dữ liệu đã được gán nhãn và lưu tại: {output_file}")
    print(f"[*] Số lượng - An toàn: {len(df[df['Target']==0])} | Mã độc: {len(df[df['Target']==1])}")

if __name__ == "__main__":
    fetch_fwaf_dataset()