#!/usr/bin/env bash
# setup-dev-env.sh — 개발 환경 설정 (컨테이너 내부 실행)
# Usage: lxc exec dev-{name} -- bash /path/to/setup-dev-env.sh {GIT_USER_NAME} {GIT_EMAIL} [GITHUB_TOKEN]
#
# 예시:
#   lxc exec dev-j2hoon10 -- bash /tmp/setup-dev-env.sh J2hoon10 myhome559755@naver.com
#   lxc exec dev-hj -- bash /tmp/setup-dev-env.sh dorae222 dhj9842@gmail.com ghp_xxxxx

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
    error "사용법: $0 <GIT_USER_NAME> <GIT_EMAIL> [GITHUB_TOKEN]"
    exit 1
fi

GIT_USER_NAME="$1"
GIT_EMAIL="$2"
GITHUB_TOKEN="${3:-}"

REPO_URL="https://github.com/dorae222/adelie-investment.git"
PROJECT_DIR="$HOME/adelie-investment"
INFRA_DIR="$PROJECT_DIR/infra"

info "Git 사용자: $GIT_USER_NAME <$GIT_EMAIL>"
if [[ -n "$GITHUB_TOKEN" ]]; then
    REPO_URL="https://${GITHUB_TOKEN}@github.com/dorae222/adelie-investment.git"
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
    git pull --rebase origin main 2>/dev/null || git pull origin main || true
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    info "클론 완료: $PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# ── Step 6: Git 설정 ──
step "Step 6/12: Git 설정"
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_EMAIL"
info "git user.name:  $(git config user.name)"
info "git user.email: $(git config user.email)"

# ── Step 7: 로컬 DB docker-compose.yml ──
step "Step 7/12: 로컬 DB 스택 구성"
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

  neo4j:
    image: neo4j:5
    container_name: adelie-neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: neo4j/adelie_neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4jdata:/data

  minio:
    image: minio/minio:latest
    container_name: adelie-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: adelie
      MINIO_ROOT_PASSWORD: adelie_minio
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  redisdata:
  neo4jdata:
  miniodata:
COMPOSE_EOF

info "docker-compose.yml 생성 완료"

# ── Step 8: DB 스택 시작 ──
step "Step 8/12: DB 스택 시작"
cd "$INFRA_DIR"
docker compose up -d
sleep 5
docker compose ps
cd "$PROJECT_DIR"

# ── Step 9: .env 생성 ──
step "Step 9/12: .env 파일 생성"

if [[ -f "$PROJECT_DIR/.env" ]]; then
    warn ".env 이미 존재. 백업 후 새로 생성합니다."
    cp "$PROJECT_DIR/.env" "$PROJECT_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)"
fi

cat > "$PROJECT_DIR/.env" << 'ENV_EOF'
# Adelie Investment 환경 변수 (setup-dev-env.sh 생성)

# --- Database ---
DATABASE_URL=postgresql+asyncpg://adelie:adelie@localhost:5432/adelie_db
SYNC_DATABASE_URL=postgresql://adelie:adelie@localhost:5432/adelie_db

# --- Redis ---
REDIS_URL=redis://localhost:6379/0

# --- Neo4j ---
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=adelie_neo4j

# --- MinIO ---
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=adelie
MINIO_SECRET_KEY=adelie_minio

# --- API Keys (직접 입력 필요) ---
OPENAI_API_KEY=your_openai_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
LANGCHAIN_API_KEY=your_langchain_api_key_here

# --- JWT ---
JWT_SECRET=adelie-dev-jwt-secret-key-change-in-production

# --- 기타 ---
ENV=development
DEBUG=true
ENV_EOF

info ".env 생성 완료"

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
    # PostgreSQL 준비 대기 (최대 30초)
    for i in $(seq 1 30); do
        docker exec adelie-postgres pg_isready -U adelie -d adelie_db > /dev/null 2>&1 && break
        [[ $i -eq 30 ]] && warn "PostgreSQL 준비 시간 초과"
        sleep 1
    done

    cd database
    ../.venv/bin/alembic upgrade head 2>&1 || warn "마이그레이션 실패. 수동: cd database && ../.venv/bin/alembic upgrade head"
    cd "$PROJECT_DIR"
fi

# ── 완료 ──
echo ""
step "개발 환경 설정 완료!"
info "프로젝트: $PROJECT_DIR"
info "Git:    $GIT_USER_NAME <$GIT_EMAIL>"
info "Python: $(python3.12 --version 2>&1)"
info "Node:   $(node --version 2>&1)"
echo ""
echo -e "${YELLOW}${BOLD}[TODO] .env에 API 키 입력:${NC}"
echo "  vi ~/adelie-investment/.env"
echo "  - OPENAI_API_KEY / PERPLEXITY_API_KEY / LANGCHAIN_API_KEY"
