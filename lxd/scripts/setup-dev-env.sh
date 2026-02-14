#!/usr/bin/env bash
# setup-dev-env.sh — 개발 환경 설정 (컨테이너 내부 실행)
#
# Usage:
#   lxc exec dev-{name} -- bash /tmp/setup-dev-env.sh <GIT_USER> <GIT_EMAIL> [OPTIONS]
#
# Options:
#   --mode shared|local     DB 모드 (기본: shared = infra-server 사용)
#   --part <name>           파트명 → dev/<name> 브랜치 자동 전환
#   --token <GITHUB_TOKEN>  GitHub 인증 토큰
#
# 예시:
#   # infra-server DB 사용 + chatbot 브랜치
#   lxc exec dev-j2hoon10 -- bash /tmp/setup-dev-env.sh J2hoon10 myhome559755@naver.com --part chatbot
#
#   # 로컬 DB + GitHub 토큰
#   lxc exec dev-hj -- bash /tmp/setup-dev-env.sh dorae222 dhj9842@gmail.com --mode local --token ghp_xxxxx

set -euo pipefail

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}${BOLD}>>> $*${NC}"; }

# ── Step 1: 인자 파싱 ──
step "Step 1/12: 인자 파싱"

if [[ $# -lt 2 ]]; then
    error "사용법: $0 <GIT_USER_NAME> <GIT_EMAIL> [--mode shared|local] [--part <name>] [--token <TOKEN>]"
    echo ""
    echo "  --mode shared   infra-server(10.10.10.10) DB 사용 (기본값)"
    echo "  --mode local    로컬 Docker DB 생성"
    echo "  --part <name>   dev/<name> 브랜치로 자동 전환 (frontend|chatbot|pipeline|backend|infra)"
    echo "  --token <TOKEN> GitHub 인증 토큰"
    exit 1
fi

GIT_USER_NAME="$1"
GIT_EMAIL="$2"
shift 2

# 옵션 기본값
DB_MODE="shared"
PART_NAME=""
GITHUB_TOKEN=""

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            DB_MODE="$2"
            if [[ "$DB_MODE" != "shared" && "$DB_MODE" != "local" ]]; then
                error "--mode는 shared 또는 local만 가능합니다"
                exit 1
            fi
            shift 2
            ;;
        --part)
            PART_NAME="$2"
            shift 2
            ;;
        --token)
            GITHUB_TOKEN="$2"
            shift 2
            ;;
        *)
            # 하위 호환: 3번째 위치 인자를 토큰으로 처리
            if [[ -z "$GITHUB_TOKEN" ]]; then
                GITHUB_TOKEN="$1"
            fi
            shift
            ;;
    esac
done

REPO_URL="https://github.com/404-NFYet/adelie-investment.git"
PROJECT_DIR="$HOME/adelie-investment"
INFRA_DIR="$PROJECT_DIR/infra"

# infra-server 연결 정보
INFRA_DB_HOST="10.10.10.10"
INFRA_DB_PORT="5432"
INFRA_DB_USER="narative"
INFRA_DB_PASS="password"
INFRA_DB_NAME="narrative_invest"

info "Git 사용자: $GIT_USER_NAME <$GIT_EMAIL>"
info "DB 모드: $DB_MODE"
[[ -n "$PART_NAME" ]] && info "파트: $PART_NAME → dev/$PART_NAME 브랜치"
if [[ -n "$GITHUB_TOKEN" ]]; then
    REPO_URL="https://${GITHUB_TOKEN}@github.com/404-NFYet/adelie-investment.git"
    info "GitHub 토큰: 제공됨"
fi

# ── Step 2: 시스템 패키지 ──
step "Step 2/12: 시스템 패키지 설치"
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq \
    build-essential software-properties-common \
    git curl wget jq ca-certificates gnupg lsb-release unzip \
    > /dev/null 2>&1

# Python 3.12
info "Python 3.12 설치..."
add-apt-repository -y ppa:deadsnakes/ppa > /dev/null 2>&1
apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3.12-dev > /dev/null 2>&1
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 2>/dev/null || true
info "Python: $(python3.12 --version)"

# ── Step 3: Docker CE ──
step "Step 3/12: Docker CE 설치"

if command -v docker &>/dev/null; then
    info "Docker 이미 설치됨: $(docker --version)"
else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin > /dev/null 2>&1
    usermod -aG docker "${SUDO_USER:-root}" 2>/dev/null || true
    info "Docker 설치 완료: $(docker --version)"
fi

systemctl enable docker 2>/dev/null || true
systemctl start docker 2>/dev/null || true

# ── Step 4: Node.js 20 ──
step "Step 4/12: Node.js 20 설치"

if command -v node &>/dev/null && node --version | grep -q "v20"; then
    info "Node.js 이미 설치됨: $(node --version)"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
    info "Node.js: $(node --version), npm: $(npm --version)"
fi

# ── Step 5: 레포지토리 클론 ──
step "Step 5/12: 레포지토리 클론"

if [[ -d "$PROJECT_DIR/.git" ]]; then
    warn "프로젝트가 이미 존재합니다. 업데이트합니다."
    cd "$PROJECT_DIR"
    git pull --rebase origin develop 2>/dev/null || git pull origin develop || true
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    info "클론 완료: $PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# develop 브랜치로 전환 (기본)
git checkout develop 2>/dev/null || true

# 파트 브랜치 전환
if [[ -n "$PART_NAME" ]]; then
    BRANCH="dev/$PART_NAME"
    info "브랜치 전환: $BRANCH"
    git fetch origin "$BRANCH" 2>/dev/null || true
    git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH" origin/"$BRANCH" 2>/dev/null || {
        warn "브랜치 $BRANCH를 찾을 수 없습니다. develop에서 생성합니다."
        git checkout -b "$BRANCH" develop
    }
fi

# ── Step 6: Git 설정 ──
step "Step 6/12: Git 설정"
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_EMAIL"
info "git user.name:  $(git config user.name)"
info "git user.email: $(git config user.email)"

# ── Step 7: 로컬 DB docker-compose.yml (local 모드만) ──
step "Step 7/12: DB 스택 구성 (모드: $DB_MODE)"

if [[ "$DB_MODE" == "local" ]]; then
    mkdir -p "$INFRA_DIR"

    cat > "$INFRA_DIR/docker-compose.yml" << 'COMPOSE_EOF'
version: "3.8"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: adelie-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: adelie_db
      POSTGRES_USER: adelie
      POSTGRES_PASSWORD: adelie
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U adelie -d adelie_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: adelie-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
COMPOSE_EOF

    info "로컬 DB docker-compose.yml 생성 완료"
else
    info "shared 모드: infra-server(${INFRA_DB_HOST}) DB 사용 — 로컬 DB 스택 생략"
fi

# ── Step 8: DB 스택 시작 (local 모드만) ──
step "Step 8/12: DB 스택 시작"

if [[ "$DB_MODE" == "local" ]]; then
    cd "$INFRA_DIR"
    docker compose up -d
    sleep 5
    docker compose ps
    cd "$PROJECT_DIR"
else
    info "shared 모드: 로컬 DB 시작 건너뜀"
    info "infra-server DB 연결 테스트..."
    if command -v pg_isready &>/dev/null; then
        pg_isready -h "$INFRA_DB_HOST" -p "$INFRA_DB_PORT" -U "$INFRA_DB_USER" 2>/dev/null \
            && info "PostgreSQL 연결 성공" \
            || warn "PostgreSQL 연결 실패 — infra-server 상태 확인 필요"
    else
        info "pg_isready 미설치 — DB 연결은 앱 실행 시 확인됩니다"
    fi
fi

# ── Step 9: .env 생성 ──
step "Step 9/12: .env 파일 생성"

if [[ -f "$PROJECT_DIR/.env" ]]; then
    warn ".env 이미 존재. 백업 후 새로 생성합니다."
    cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
fi

if [[ "$DB_MODE" == "shared" ]]; then
    cat > "$PROJECT_DIR/.env" << ENV_EOF
# Adelie Investment 환경 변수 (setup-dev-env.sh 생성)
# 모드: shared (infra-server DB)

# --- Database (infra-server) ---
DATABASE_URL=postgresql+asyncpg://${INFRA_DB_USER}:${INFRA_DB_PASS}@${INFRA_DB_HOST}:${INFRA_DB_PORT}/${INFRA_DB_NAME}
SYNC_DATABASE_URL=postgresql://${INFRA_DB_USER}:${INFRA_DB_PASS}@${INFRA_DB_HOST}:${INFRA_DB_PORT}/${INFRA_DB_NAME}

# --- Redis (infra-server) ---
REDIS_URL=redis://${INFRA_DB_HOST}:6379/0

# --- MinIO (infra-server) ---
MINIO_ENDPOINT=${INFRA_DB_HOST}:9000
MINIO_ACCESS_KEY=adelie
MINIO_SECRET_KEY=adelie_minio

# --- API Keys (팀 공유 — 직접 입력 필요) ---
OPENAI_API_KEY=your_openai_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
LANGCHAIN_API_KEY=your_langchain_api_key_here

# --- LangSmith ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=v.1.contents_generation

# --- JWT ---
JWT_SECRET=adelie-dev-jwt-secret-key-change-in-production

# --- 기타 ---
ENV=development
DEBUG=true
ENV_EOF
else
    cat > "$PROJECT_DIR/.env" << 'ENV_EOF'
# Adelie Investment 환경 변수 (setup-dev-env.sh 생성)
# 모드: local (로컬 Docker DB)

# --- Database (로컬) ---
DATABASE_URL=postgresql+asyncpg://adelie:adelie@localhost:5432/adelie_db
SYNC_DATABASE_URL=postgresql://adelie:adelie@localhost:5432/adelie_db

# --- Redis (로컬) ---
REDIS_URL=redis://localhost:6379/0

# --- MinIO ---
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=adelie
MINIO_SECRET_KEY=adelie_minio

# --- API Keys (팀 공유 — 직접 입력 필요) ---
OPENAI_API_KEY=your_openai_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
LANGCHAIN_API_KEY=your_langchain_api_key_here

# --- LangSmith ---
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=v.1.contents_generation

# --- JWT ---
JWT_SECRET=adelie-dev-jwt-secret-key-change-in-production

# --- 기타 ---
ENV=development
DEBUG=true
ENV_EOF
fi

info ".env 생성 완료 (모드: $DB_MODE)"

# ── Step 10: Python venv + 의존성 ──
step "Step 10/12: Python 가상환경 + 의존성 설치"
cd "$PROJECT_DIR"

if [[ ! -d ".venv" ]]; then
    python3.12 -m venv .venv
fi
.venv/bin/pip install --upgrade pip > /dev/null 2>&1

for req in fastapi/requirements.txt datapipeline/requirements.txt chatbot/requirements.txt; do
    if [[ -f "$req" ]]; then
        info "$req 설치 중..."
        .venv/bin/pip install -r "$req" > /dev/null 2>&1
    fi
done
info "주요 패키지:"
.venv/bin/pip list 2>/dev/null | grep -iE "fastapi|pykrx|sqlalchemy|alembic|langchain" || true

# ── Step 11: Node.js 의존성 ──
step "Step 11/12: Node.js 의존성 (frontend)"

if [[ -d "frontend" ]]; then
    cd frontend && npm install > /dev/null 2>&1 && cd "$PROJECT_DIR"
    info "npm install 완료"
fi

# ── Step 12: Alembic 마이그레이션 ──
step "Step 12/12: Alembic 마이그레이션"

if [[ -d "database" && -f "database/alembic.ini" ]]; then
    if [[ "$DB_MODE" == "local" ]]; then
        # 로컬 PostgreSQL 준비 대기 (최대 30초)
        for i in $(seq 1 30); do
            docker exec adelie-postgres pg_isready -U adelie -d adelie_db > /dev/null 2>&1 && break
            [[ $i -eq 30 ]] && warn "PostgreSQL 준비 시간 초과"
            sleep 1
        done
    fi

    cd database
    ../.venv/bin/alembic upgrade head 2>&1 || warn "마이그레이션 실패. 수동: cd database && ../.venv/bin/alembic upgrade head"
    cd "$PROJECT_DIR"
fi

# ── 완료 ──
echo ""
step "개발 환경 설정 완료!"
info "프로젝트: $PROJECT_DIR"
info "Git:     $GIT_USER_NAME <$GIT_EMAIL>"
info "브랜치:  $(git branch --show-current)"
info "DB 모드: $DB_MODE"
info "Python:  $(python3.12 --version 2>&1)"
info "Node:    $(node --version 2>&1)"
echo ""

if grep -q "your_openai_api_key_here" "$PROJECT_DIR/.env" 2>/dev/null; then
    echo -e "${YELLOW}${BOLD}[TODO] .env에 API 키 입력:${NC}"
    echo "  vi ~/adelie-investment/.env"
    echo "  - OPENAI_API_KEY / PERPLEXITY_API_KEY / LANGCHAIN_API_KEY"
fi
