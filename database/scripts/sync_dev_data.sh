#!/bin/bash
# database/scripts/sync_dev_data.sh
# deploy-test 프로덕션 DB의 콘텐츠 테이블을 개발 DB에 동기화한다.
#
# 사용법:
#   bash database/scripts/sync_dev_data.sh [target_db_url]
#
# 기본 대상: infra-server 공유 dev DB
# 예시:
#   bash database/scripts/sync_dev_data.sh postgresql://narative:password@localhost:5433/narrative_invest
#
# 전제조건:
#   - deploy-test SSH 접속 가능 (ssh deploy-test)
#   - psql 클라이언트 설치 (apt install postgresql-client)
#   - 대상 DB에 스키마가 이미 존재해야 함 (alembic upgrade head 완료 상태)

set -euo pipefail

TARGET_URL="${1:-postgresql://narative:password@10.10.10.10:5432/narrative_invest}"
PROD_HOST="deploy-test"
PROD_CONTAINER="adelie-postgres"
PROD_DB="narrative_invest"
PROD_USER="narative"

# 동기화할 콘텐츠 테이블 (스키마 테이블 제외)
CONTENT_TABLES=(
  "stock_listings"
  "daily_briefings"
  "briefing_stocks"
  "historical_cases"
  "case_matches"
  "case_stock_relations"
  "broker_reports"
)

echo "=== deploy-test → dev DB 콘텐츠 동기화 ==="
echo "대상 DB: ${TARGET_URL}"
echo ""

# psql 클라이언트 확인
if ! command -v psql &>/dev/null; then
  echo "❌ psql을 찾을 수 없습니다. postgresql-client를 설치하세요:"
  echo "   sudo apt install postgresql-client"
  exit 1
fi

# deploy-test SSH 접속 확인
if ! ssh -o ConnectTimeout=5 "${PROD_HOST}" "echo ok" &>/dev/null; then
  echo "❌ ${PROD_HOST} SSH 접속 실패. ~/.ssh/config 또는 SSH 키를 확인하세요."
  exit 1
fi

echo "✅ deploy-test SSH 접속 확인"
echo ""

# 테이블별 덤프 & 적용
for tbl in "${CONTENT_TABLES[@]}"; do
  echo -n "  ${tbl} 동기화 중... "

  # prod에서 data-only 덤프 → 대상 DB에 직접 적용
  # TRUNCATE CASCADE로 기존 데이터 삭제 후 INSERT
  ssh "${PROD_HOST}" \
    "docker exec ${PROD_CONTAINER} pg_dump \
      -U ${PROD_USER} -d ${PROD_DB} \
      -t ${tbl} --data-only --disable-triggers \
      --column-inserts 2>/dev/null" \
  | (
    # TRUNCATE 먼저 실행 (FK 제약 비활성화)
    echo "SET session_replication_role = replica;"
    echo "TRUNCATE TABLE ${tbl} CASCADE;"
    cat
    echo "SET session_replication_role = DEFAULT;"
  ) \
  | psql "${TARGET_URL}" -q 2>/dev/null

  echo "✅"
done

echo ""
echo "=== 동기화 완료 ==="
echo ""
echo "데이터 확인:"
psql "${TARGET_URL}" -c \
  "SELECT 'daily_briefings' AS tbl, count(*) FROM daily_briefings
   UNION ALL SELECT 'historical_cases', count(*) FROM historical_cases
   UNION ALL SELECT 'stock_listings', count(*) FROM stock_listings;" \
  2>/dev/null || echo "  (테이블 확인 실패 — DB 접속 정보를 확인하세요)"
