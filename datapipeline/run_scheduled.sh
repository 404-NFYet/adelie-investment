#!/bin/bash
# 데이터 파이프라인 자동 실행 스크립트 (9:00 KST)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "${SCRIPT_DIR}/logs"
LOG_FILE="${SCRIPT_DIR}/logs/pipeline_$(date +%Y%m%d_%H%M%S).log"

echo "=== 데이터 파이프라인 시작: $(date) ===" | tee -a "$LOG_FILE"

# Job lock (동시 실행 방지)
LOCK_FILE="/tmp/adelie_pipeline.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "이미 파이프라인 실행 중 (lock: $LOCK_FILE)" | tee -a "$LOG_FILE"
    exit 0
fi
trap "rm -f $LOCK_FILE" EXIT
touch "$LOCK_FILE"

# 1. 시장 데이터 수집 (keyword_pipeline_graph.py - LangGraph enriched 파이프라인)
echo "[1/2] 시장 데이터 수집 중..." | tee -a "$LOG_FILE"
timeout 1800 docker exec adelie-backend-api python /app/scripts/keyword_pipeline_graph.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "시장 데이터 수집 완료" | tee -a "$LOG_FILE"
else
    echo "시장 데이터 수집 실패 (상세 로그: $LOG_FILE)" | tee -a "$LOG_FILE"
    tail -5 "$LOG_FILE"
    exit 1
fi

# 2. 역사적 사례 생성 (generate_cases.py)
echo "[2/2] 역사적 사례 생성 중..." | tee -a "$LOG_FILE"
timeout 1800 docker exec adelie-backend-api python /app/scripts/generate_cases.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "역사적 사례 생성 완료" | tee -a "$LOG_FILE"
else
    echo "역사적 사례 생성 실패 (상세 로그: $LOG_FILE)" | tee -a "$LOG_FILE"
    tail -5 "$LOG_FILE"
    exit 1
fi

echo "=== 데이터 파이프라인 완료: $(date) ===" | tee -a "$LOG_FILE"
echo "로그 파일: $LOG_FILE" | tee -a "$LOG_FILE"
