#!/usr/bin/env bash
# =============================================================
# sync_dev_data.sh — deploy-test → LXD 콘텐츠 데이터 동기화
#
# 사용법:
#   bash database/scripts/sync_dev_data.sh              # 전체 5대
#   bash database/scripts/sync_dev_data.sh dev-ryejinn  # 단일 서버
# =============================================================
set -euo pipefail

# ── 설정 ──
DEPLOY_HOST="deploy-test"
PROD_CONTAINER="adelie-postgres"
DB_NAME="narrative_invest"
DB_USER="narative"
DUMP_FILE="/tmp/adelie-content-dump-$(date +%Y%m%d%H%M%S).sql"
LXD_SERVERS=(dev-yj99son dev-j2hoon10 dev-ryejinn dev-jjjh02 dev-hj)

# 콘텐츠 테이블 (Tier 0 → 1 → 2 순서, FK 의존성 고려)
TABLES=(
    # Tier 0: 참조 테이블
    stock_listings
    market_daily_history
    stock_daily_history
    glossary
    company_relations
    broker_reports
    # Tier 1: 메인 콘텐츠
    daily_briefings
    daily_narratives
    historical_cases
    # Tier 2: 자식 (FK → Tier 1)
    briefing_stocks
    narrative_scenarios
    case_stock_relations
    case_matches
)

# ── 색상 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[sync]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

# ── 대상 서버 결정 ──
if [[ $# -ge 1 ]]; then
    TARGET_SERVERS=("$1")
    log "단일 서버 모드: $1"
else
    TARGET_SERVERS=("${LXD_SERVERS[@]}")
    log "전체 서버 모드: ${LXD_SERVERS[*]}"
fi

# ── Step 1: deploy-test에서 pg_dump ──
log "Step 1/3: deploy-test에서 콘텐츠 데이터 덤프..."

TABLE_ARGS=""
for t in "${TABLES[@]}"; do
    TABLE_ARGS+="--table=${t} "
done

ssh "$DEPLOY_HOST" "docker exec ${PROD_CONTAINER} pg_dump \
    -U ${DB_USER} -d ${DB_NAME} \
    --data-only --no-owner --disable-triggers \
    ${TABLE_ARGS}" > "$DUMP_FILE"

DUMP_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
ok "덤프 완료: ${DUMP_FILE} (${DUMP_SIZE})"

# 덤프 파일이 비어있으면 중단
if [[ ! -s "$DUMP_FILE" ]]; then
    err "덤프 파일이 비어있습니다. deploy-test DB를 확인하세요."
    rm -f "$DUMP_FILE"
    exit 1
fi

# ── Step 2: 복원 SQL 래퍼 생성 ──
log "Step 2/3: 복원 SQL 생성..."

RESTORE_FILE="/tmp/adelie-content-restore-$(date +%Y%m%d%H%M%S).sql"

# TRUNCATE 목록 (역순 — 자식 먼저)
TRUNCATE_LIST=""
for (( i=${#TABLES[@]}-1; i>=0; i-- )); do
    if [[ -n "$TRUNCATE_LIST" ]]; then
        TRUNCATE_LIST+=", "
    fi
    TRUNCATE_LIST+="${TABLES[$i]}"
done

cat > "$RESTORE_FILE" << EOSQL
-- 자동 생성: sync_dev_data.sh
BEGIN;

-- FK 트리거 비활성화
SET session_replication_role = 'replica';

-- 기존 데이터 삭제 (CASCADE)
TRUNCATE ${TRUNCATE_LIST} CASCADE;

-- 덤프 데이터 복원
$(cat "$DUMP_FILE")

-- 시퀀스 리셋
$(for t in "${TABLES[@]}"; do
    echo "SELECT setval(pg_get_serial_sequence('${t}', 'id'), COALESCE((SELECT MAX(id) FROM ${t}), 1)) WHERE pg_get_serial_sequence('${t}', 'id') IS NOT NULL;"
done)

-- FK 트리거 복원
SET session_replication_role = 'origin';

COMMIT;
EOSQL

RESTORE_SIZE=$(du -h "$RESTORE_FILE" | cut -f1)
ok "복원 SQL 생성 완료: ${RESTORE_FILE} (${RESTORE_SIZE})"

# ── Step 3: 각 LXD 서버에 복원 ──
log "Step 3/3: LXD 서버에 데이터 복원..."

SUCCESS=0
FAIL=0

for SERVER in "${TARGET_SERVERS[@]}"; do
    log "  → ${SERVER} 처리 중..."

    # LXD 서버 내 postgres 컨테이너 자동탐지
    PG_CONTAINER=$(lxc exec "$SERVER" -- bash -c "docker ps --format '{{.Names}}' | grep postgres | head -1" 2>/dev/null || true)

    if [[ -z "$PG_CONTAINER" ]]; then
        warn "  ${SERVER}: postgres 컨테이너 미발견 (건너뜀)"
        ((FAIL++)) || true
        continue
    fi

    # 파일 전송
    lxc file push "$RESTORE_FILE" "${SERVER}/tmp/adelie-restore.sql" 2>/dev/null

    # 복원 실행
    if lxc exec "$SERVER" -- bash -c "docker exec -i ${PG_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} < /tmp/adelie-restore.sql" > /dev/null 2>&1; then
        # 검증: daily_briefings 행 수 확인
        COUNT=$(lxc exec "$SERVER" -- bash -c "docker exec ${PG_CONTAINER} psql -U ${DB_USER} -d ${DB_NAME} -tAc 'SELECT COUNT(*) FROM daily_briefings'" 2>/dev/null || echo "?")
        ok "  ${SERVER}: 복원 완료 (daily_briefings: ${COUNT}행, pg: ${PG_CONTAINER})"
        ((SUCCESS++)) || true
    else
        err "  ${SERVER}: 복원 실패"
        ((FAIL++)) || true
    fi

    # 임시 파일 정리
    lxc exec "$SERVER" -- rm -f /tmp/adelie-restore.sql 2>/dev/null || true
done

# ── 정리 ──
rm -f "$DUMP_FILE" "$RESTORE_FILE"

echo ""
log "=== 동기화 완료 ==="
log "성공: ${SUCCESS}대 / 실패: ${FAIL}대 / 전체: ${#TARGET_SERVERS[@]}대"

if [[ $FAIL -gt 0 ]]; then
    exit 1
fi
