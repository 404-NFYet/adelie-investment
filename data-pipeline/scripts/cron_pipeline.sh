#!/bin/bash
# 데이터 파이프라인 스케줄링 스크립트
# cron 등록: 0 7 * * 1-5 /path/to/cron_pipeline.sh
# 평일 오전 7시 실행 (장 시작 전)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIPELINE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$PIPELINE_DIR")"
LOG_DIR="${PROJECT_ROOT}/logs"
DATE=$(date +%Y%m%d)

mkdir -p "$LOG_DIR"

echo "[$(date)] Pipeline cron started" >> "${LOG_DIR}/pipeline_${DATE}.log"

# 가상환경 활성화 (있을 경우)
if [ -f "${PROJECT_ROOT}/venv/bin/activate" ]; then
    source "${PROJECT_ROOT}/venv/bin/activate"
fi

# .env 로드
export $(grep -v '^#' "${PROJECT_ROOT}/.env" | xargs 2>/dev/null)

# 파이프라인 실행 (stock + report)
cd "$PIPELINE_DIR"
python run_pipeline.py --stock --report >> "${LOG_DIR}/pipeline_${DATE}.log" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date)] Pipeline completed successfully" >> "${LOG_DIR}/pipeline_${DATE}.log"
else
    echo "[$(date)] Pipeline failed with exit code: $EXIT_CODE" >> "${LOG_DIR}/pipeline_${DATE}.log"
fi

# 7일 이상 된 로그 정리
find "$LOG_DIR" -name "pipeline_*.log" -mtime +7 -delete 2>/dev/null

exit $EXIT_CODE
