import requests
import random
import time

TARGET_URL = "http://localhost:8000/tienda1/global/estilos.css"

# Tạo ngẫu nhiên 5 cái IP giả mạo
fake_ips = [f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}" for _ in range(5)]

print(f"Bắt đầu mô phỏng tấn công từ {len(fake_ips)} IP khác nhau...")

for i in range(20): # Bắn 20 requests liên tục
    # Chọn bừa 1 IP trong danh sách
    current_ip = random.choice(fake_ips)
    
    # Gắn IP giả vào Header
    headers = {"X-Fake-IP": current_ip}
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        print(f"[Request {i+1}] Từ IP: {current_ip:<15} | Status: {response.status_code}")
    except Exception as e:
        print(f"Lỗi kết nối: {e}")
        
    time.sleep(0.2) # Nghỉ 0.2s giữa các lần bắn