# --- Giai đoạn 1: Biên dịch mã nguồn React ---
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Giai đoạn 2: Khởi chạy môi trường máy chủ Nginx thực tế ---
FROM nginx:alpine
# Copy toàn bộ file tĩnh sau khi build vào thư mục gốc của Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Ghi đè file cấu hình mặc định của Nginx để xử lý định tuyến React Router (nếu có)
RUN echo 'server { listen 80; location / { root /usr/share/nginx/html; index index.html; try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]