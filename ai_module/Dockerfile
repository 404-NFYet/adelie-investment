# ============================================================
# Adelie Investment - AI Module (Pipeline Worker)
# ============================================================
FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 파이프라인 실행 (기본 명령어)
CMD ["python", "-m", "pipeline.main"]
