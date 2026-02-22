# ============================================================
# Adelie Investment - FastAPI Backend (멀티스테이지 빌드)
# ============================================================

# ── Builder: 컴파일 도구 포함, Python 패키지 설치 ──
FROM python:3.11-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY fastapi/requirements.txt /tmp/requirements.txt
RUN pip install --user --no-cache-dir -r /tmp/requirements.txt


# ── Runtime: 빌드 도구 제외, 최소 런타임만 포함 ──
FROM python:3.11-slim

# 런타임 시스템 의존성만 설치 (libpq5: PostgreSQL 클라이언트 라이브러리)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# builder에서 설치된 Python 패키지 복사
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# 소스 복사
COPY fastapi/ ./
COPY shared/ ./shared/
COPY chatbot/ ./chatbot/
COPY datapipeline/ ./datapipeline/
COPY database/ ./database/

# 기존 경로 호환 심링크 (scheduler, pipeline route)
RUN ln -sf /app/datapipeline/scripts /app/scripts && \
    ln -sf /app/datapipeline/collectors /app/collectors

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8082/api/v1/health || exit 1

EXPOSE 8082
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8082 --workers ${WEB_CONCURRENCY:-4}"]
