#!/bin/bash
# 데이터 파이프라인 자동 실행 스크립트 (9:00 KST)

LOG_FILE="/home/ubuntu/adelie-investment/pipeline_$(date +%Y%m%d_%H%M%S).log"
echo "=== 데이터 파이프라인 시작: $(date) ===" | tee -a "$LOG_FILE"

# 1. 시장 데이터 수집 (seed_fresh_data.py)
echo "[1/2] 시장 데이터 수집 중..." | tee -a "$LOG_FILE"
docker exec adelie-backend-api python /app/scripts/seed_fresh_data.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 시장 데이터 수집 완료" | tee -a "$LOG_FILE"
else
    echo "❌ 시장 데이터 수집 실패" | tee -a "$LOG_FILE"
    exit 1
fi

# 2. 역사적 사례 생성 (generate_cases.py)
echo "[2/2] 역사적 사례 생성 중..." | tee -a "$LOG_FILE"
docker exec adelie-backend-api python /app/generate_cases.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 역사적 사례 생성 완료" | tee -a "$LOG_FILE"
else
    echo "❌ 역사적 사례 생성 실패" | tee -a "$LOG_FILE"
    exit 1
fi

echo "=== 데이터 파이프라인 완료: $(date) ===" | tee -a "$LOG_FILE"
echo "로그 파일: $LOG_FILE" | tee -a "$LOG_FILE"
