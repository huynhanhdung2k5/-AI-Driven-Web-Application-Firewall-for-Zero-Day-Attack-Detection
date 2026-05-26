import requests
import pandas as pd

# ==========================================
# 1. ĐỊNH TUYẾN TỚI KHO VŨ KHÍ SECLISTS (RAW GITHUB LINKS)
# ==========================================
SECLISTS_URLS = {
    "SQL_Injection": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Quick-SQLi.txt",
    "Cross_Site_Scripting": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS/XSS-Bypass-Strings-BruteForce.txt",
    "Local_File_Inclusion": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-gracefulsecurity-linux.txt",
    "Command_Injection": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/command-injection-commix.txt",
    "Bad_User_Agents": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/User-Agents/bad-user-agents.txt"
}

def fetch_and_process_data():
    print("[*] Đang khởi động chiến dịch thu thập dữ liệu từ SecLists...")
    malicious_payloads = []

    for attack_type, url in SECLISTS_URLS.items():
        print(f" -> Đang cào dữ liệu: {attack_type}...")
        try:
            # Tải nội dung text trực tiếp từ Github
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                lines = response.text.split('\n')
                
                for line in lines:
                    payload = line.strip()
                    # Bỏ qua các dòng trống hoặc dòng comment
                    if payload and not payload.startswith('#'): 
                        
                        # ==========================================
                        # 2. CHUẨN HÓA DỮ LIỆU ĐỂ GIỐNG CSIC DATASET
                        # WAF của bạn quen đọc: "GET /path HTTP/1.1"
                        # Nên ta phải bọc mã độc vào cấu trúc HTTP
                        # ==========================================
                        if attack_type == "Bad_User_Agents":
                            simulated_req = f"GET / HTTP/1.1\nUser-Agent: {payload}"
                        else:
                            simulated_req = f"GET /search?query={payload} HTTP/1.1"
                            
                        malicious_payloads.append(simulated_req)
            else:
                print(f" [!] Lỗi HTTP {response.status_code} khi cào {attack_type}")
                
        except Exception as e:
            print(f" [!] Mất kết nối khi cào {attack_type}: {e}")

    # ==========================================
    # 3. ĐÓNG GÓI THÀNH DATAFRAME VÀ GÁN NHÃN (LABELING)
    # ==========================================
    # Gán Target = 1 (Tương đương với nhãn "Mã độc/Bất thường")
    df_new = pd.DataFrame({
        "Full_Payload": malicious_payloads,
        "Target": 1  
    })

    # Xóa các dòng trùng lặp (nếu có)
    df_new = df_new.drop_duplicates()

    print(f"\n[*] TUYỆT VỜI! Đã thu thập và chuẩn hóa thành công {len(df_new)} requests độc hại mới!")
    
    # Lưu ra file CSV
    output_file = "seclists_malicious_update.csv"
    df_new.to_csv(output_file, index=False)
    print(f"[*] Dữ liệu đã được đóng gói an toàn vào: {output_file}")

if __name__ == "__main__":
    fetch_and_process_data()