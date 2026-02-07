# ============================================================
# Adelie Investment - Frontend (React + Vite + Nginx)
# ============================================================
FROM node:20-alpine AS builder
WORKDIR /app

# 의존성 설치 (캐시 최적화)
COPY package*.json ./
RUN npm ci --silent

# 소스 복사 + 빌드
COPY . .
ARG VITE_FASTAPI_URL=""
ARG VITE_SPRING_URL=""
RUN npm run build

# ============================================================
# Runtime: nginx
# ============================================================
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
