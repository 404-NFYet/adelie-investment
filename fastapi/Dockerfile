# ============================================================
# Adelie Investment - FastAPI Backend
# ============================================================
FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치 (캐시 최적화)
COPY fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY fastapi/ ./
COPY shared/ ./shared/
COPY chatbot/ ./chatbot/
COPY datapipeline/scripts/ ./scripts/
COPY datapipeline/collectors/ ./collectors/
COPY datapipeline/prompts/ ./datapipeline/prompts/

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8082/api/v1/health || exit 1

EXPOSE 8082
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8082 --workers ${WEB_CONCURRENCY:-4}"]
