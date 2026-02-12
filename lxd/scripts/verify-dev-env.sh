#!/usr/bin/env bash
# verify-dev-env.sh — 5개 개발 컨테이너 환경 일괄 점검
# Usage: bash verify-dev-env.sh

set -euo pipefail

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
SKIP="${YELLOW}-${NC}"

# 컨테이너 + 기대 git config
declare -A EXPECTED_NAME EXPECTED_EMAIL
CONTAINERS=("dev-yj99son" "dev-j2hoon10" "dev-ryejinn" "dev-jjjh02" "dev-hj")

EXPECTED_NAME["dev-yj99son"]="YJ99Son"
EXPECTED_NAME["dev-j2hoon10"]="J2hoon10"
EXPECTED_NAME["dev-ryejinn"]="ryejinn"
EXPECTED_NAME["dev-jjjh02"]="jjjh02"
EXPECTED_NAME["dev-hj"]="dorae222"

EXPECTED_EMAIL["dev-yj99son"]="syjin2008@naver.com"
EXPECTED_EMAIL["dev-j2hoon10"]="myhome559755@naver.com"
EXPECTED_EMAIL["dev-ryejinn"]="arj1018@ewhain.net"
EXPECTED_EMAIL["dev-jjjh02"]="jinnyshur0104@gmail.com"
EXPECTED_EMAIL["dev-hj"]="dhj9842@gmail.com"

PROJECT_DIR="adelie-investment"
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0

# 컨테이너 내 명령 실행
lxc_exec() {
    local ct="$1"
    shift
    lxc exec "$ct" -- bash -c "$*" 2>/dev/null
}

# 점검 함수 (결과를 변수에 저장)
check() {
    local ct="$1" label="$2" cmd="$3" expected="${4:-}"
    local result

    result=$(lxc_exec "$ct" "$cmd" 2>/dev/null) || result=""

    if [[ -n "$expected" ]]; then
        if [[ "$result" == *"$expected"* ]]; then
            echo -e "  $PASS $label: $result"
            ((TOTAL_PASS++)) || true
        else
            echo -e "  $FAIL $label: '$result' (기대: '$expected')"
            ((TOTAL_FAIL++)) || true
        fi
    else
        if [[ -n "$result" ]]; then
            echo -e "  $PASS $label: $result"
            ((TOTAL_PASS++)) || true
        else
            echo -e "  $FAIL $label: 확인 불가"
            ((TOTAL_FAIL++)) || true
        fi
    fi
}

# 메인
echo -e "${CYAN}${BOLD}=== Adelie Investment 개발 환경 일괄 점검 ===${NC}"
echo -e "점검 대상: ${#CONTAINERS[@]}개 컨테이너"
echo ""

for ct in "${CONTAINERS[@]}"; do
    echo -e "${CYAN}${BOLD}── $ct ──${NC}"

    # 0. 컨테이너 실행 상태
    STATUS=$(lxc list --format csv -c ns "$ct" 2>/dev/null | cut -d',' -f2)
    if [[ "$STATUS" != "RUNNING" ]]; then
        echo -e "  $FAIL 컨테이너 상태: $STATUS (RUNNING 아님)"
        ((TOTAL_FAIL++)) || true
        echo ""
        continue
    fi
    echo -e "  $PASS 컨테이너 상태: RUNNING"
    ((TOTAL_PASS++)) || true

    # 1. Git 레포 존재 + 브랜치
    check "$ct" "Git 레포" "test -d ~/$PROJECT_DIR/.git && echo 'exists' || echo ''" "exists"
    check "$ct" "Git 브랜치" "cd ~/$PROJECT_DIR && git branch --show-current" "main"

    # 2. Git config
    check "$ct" "git user.name" "cd ~/$PROJECT_DIR && git config user.name" "${EXPECTED_NAME[$ct]}"
    check "$ct" "git user.email" "cd ~/$PROJECT_DIR && git config user.email" "${EXPECTED_EMAIL[$ct]}"

    # 3. Python
    check "$ct" "Python 버전" "python3.12 --version 2>/dev/null | head -1"
    check "$ct" ".venv 존재" "test -d ~/$PROJECT_DIR/.venv && echo 'exists' || echo ''" "exists"
    check "$ct" "fastapi 패키지" "~/$PROJECT_DIR/.venv/bin/pip show fastapi 2>/dev/null | grep Version || echo ''" "Version"

    # 4. Node.js
    check "$ct" "Node.js 버전" "node --version 2>/dev/null" "v20"
    check "$ct" "node_modules" "test -d ~/$PROJECT_DIR/frontend/node_modules && echo 'exists' || echo ''" "exists"

    # 5. Docker
    check "$ct" "Docker 데몬" "systemctl is-active docker 2>/dev/null" "active"
    check "$ct" "PostgreSQL" "docker ps --format '{{.Names}}' 2>/dev/null | grep -q adelie-postgres && echo 'running' || echo ''" "running"
    check "$ct" "Redis" "docker ps --format '{{.Names}}' 2>/dev/null | grep -q adelie-redis && echo 'running' || echo ''" "running"
    check "$ct" "Neo4j" "docker ps --format '{{.Names}}' 2>/dev/null | grep -q adelie-neo4j && echo 'running' || echo ''" "running"
    check "$ct" "MinIO" "docker ps --format '{{.Names}}' 2>/dev/null | grep -q adelie-minio && echo 'running' || echo ''" "running"

    # 6. .env + localhost DB
    check "$ct" ".env 존재" "test -f ~/$PROJECT_DIR/.env && echo 'exists' || echo ''" "exists"
    check "$ct" "DB URL localhost" "grep DATABASE_URL ~/$PROJECT_DIR/.env 2>/dev/null | head -1" "localhost"

    echo ""
done

# 요약
echo -e "${CYAN}${BOLD}=== 점검 결과 요약 ===${NC}"
echo -e "  ${GREEN}통과: $TOTAL_PASS${NC}"
echo -e "  ${RED}실패: $TOTAL_FAIL${NC}"

if [[ $TOTAL_FAIL -eq 0 ]]; then
    echo -e "\n${GREEN}${BOLD}모든 점검 통과!${NC}"
else
    echo -e "\n${RED}${BOLD}${TOTAL_FAIL}건 실패 — 위 로그를 확인하세요.${NC}"
    exit 1
fi
