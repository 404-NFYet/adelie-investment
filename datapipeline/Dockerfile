# ============================================================
# Adelie Investment - Data Pipeline
# ============================================================
FROM python:3.11-slim
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY datapipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY datapipeline/ ./datapipeline/
COPY fastapi/app/ ./app/

CMD ["python", "-m", "datapipeline.scripts.keyword_pipeline_graph"]
