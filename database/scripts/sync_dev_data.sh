#!/bin/bash
# database/scripts/sync_dev_data.sh
# deploy-test 프로덕션 DB 전체를 개발 DB에 동기화한다.
# alembic_version은 제외 (스키마 버전은 대상 DB의 것을 유지)
#
# 사용법:
#   bash database/scripts/sync_dev_data.sh [target_db_url]
#
# 기본 대상: 로컬 dev DB (localhost:5433)
# 예시:
#   bash database/scripts/sync_dev_data.sh postgresql://narative:password@localhost:5433/narrative_invest
#
# 전제조건:
#   - deploy-test SSH 접속 가능 (ssh deploy-test)
#   - psql 클라이언트 설치 (apt install postgresql-client)
#   - 대상 DB에 스키마가 이미 존재해야 함 (alembic upgrade head 완료 상태)

set -euo pipefail

TARGET_URL="${1:-postgresql://narative:password@localhost:5433/narrative_invest}"
PROD_HOST="deploy-test"
PROD_CONTAINER="adelie-postgres"
PROD_DB="narrative_invest"
PROD_USER="narative"

# alembic_version을 제외한 전체 테이블 (31개)
# FK 의존성 기준 정렬 (부모 → 자식 순)
ALL_TABLES=(
  "users"
  "stock_listings"
  "glossary"
  "company_relations"
  "market_daily_history"
  "stock_daily_history"
  "daily_briefings"
  "historical_cases"
  "daily_narratives"
  "broker_reports"
  "user_portfolios"
  "user_settings"
  "watchlists"
  "briefing_stocks"
  "case_matches"
  "narrative_scenarios"
  "case_stock_relations"
  "portfolio_holdings"
  "tutor_sessions"
  "learning_progress"
  "notifications"
  "simulation_trades"
  "limit_orders"
  "usage_events"
  "tutor_messages"
  "briefing_feedback"
  "briefing_rewards"
  "dwell_rewards"
  "feedback_surveys"
  "content_reactions"
  "user_feedback"
)

echo "=== deploy-test → dev DB 전체 동기화 ==="
echo "대상 DB: ${TARGET_URL}"
echo "동기화 테이블: ${#ALL_TABLES[@]}개 (alembic_version 제외)"
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

# 임시 파일 (dump + restore script)
DUMP_FILE=$(mktemp /tmp/adelie_dump_XXXXXX.sql)
RESTORE_FILE=$(mktemp /tmp/adelie_restore_XXXXXX.sql)
trap "rm -f ${DUMP_FILE} ${RESTORE_FILE}" EXIT

# prod에서 전체 데이터 덤프 (alembic_version 제외)
echo "  prod 전체 덤프 생성 중..."
ssh "${PROD_HOST}" \
  "docker exec ${PROD_CONTAINER} pg_dump \
    -U ${PROD_USER} -d ${PROD_DB} \
    --data-only --disable-triggers \
    --exclude-table=alembic_version \
    2>/dev/null" > "${DUMP_FILE}"

DUMP_SIZE=$(wc -c < "${DUMP_FILE}")
DUMP_HUMAN=$(numfmt --to=iec-i "${DUMP_SIZE}" 2>/dev/null || echo "${DUMP_SIZE} bytes")
echo "  덤프 완료: ${DUMP_HUMAN}"
echo ""

# TRUNCATE 대상: 전체 테이블 (자식 → 부모 역순, CASCADE 사용)
TABLES_CSV=$(printf "public.%s, " "${ALL_TABLES[@]}" | sed 's/, $//')

# restore 스크립트 생성: FK 비활성화 → TRUNCATE ALL → INSERT ALL → FK 활성화
{
  echo "SET session_replication_role = replica;"
  echo "TRUNCATE TABLE ${TABLES_CSV} CASCADE;"
  cat "${DUMP_FILE}"
  echo "SET session_replication_role = DEFAULT;"
} > "${RESTORE_FILE}"

# 대상 DB에 복원
echo "  대상 DB 복원 중..."
psql "${TARGET_URL}" -q -f "${RESTORE_FILE}" 2>/dev/null

echo "✅ 복원 완료"
echo ""

# 결과 확인 (주요 테이블)
echo "=== 동기화 완료 ==="
echo ""
echo "데이터 확인:"
psql "${TARGET_URL}" -c "
  SELECT 'users'            AS 테이블, count(*) AS 건수 FROM users
  UNION ALL SELECT 'stock_listings',   count(*) FROM stock_listings
  UNION ALL SELECT 'daily_briefings',  count(*) FROM daily_briefings
  UNION ALL SELECT 'historical_cases', count(*) FROM historical_cases
  UNION ALL SELECT 'glossary',         count(*) FROM glossary
  UNION ALL SELECT 'tutor_sessions',   count(*) FROM tutor_sessions
  UNION ALL SELECT 'tutor_messages',   count(*) FROM tutor_messages
  ORDER BY 1;" \
  2>/dev/null || echo "  (테이블 확인 실패 — DB 접속 정보를 확인하세요)"
