#!/bin/bash
# Narrative Investment - Infrastructure Setup Script
# infra-server (10.10.10.10)에서 실행
# 4개 서비스: PostgreSQL, Redis, Neo4j, MinIO 통합 관리

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

echo "================================================"
echo " Narrative Investment Infrastructure Setup"
echo "================================================"

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed. Please install Docker first."
    exit 1
fi

# Docker Compose 확인
if ! docker compose version &> /dev/null; then
    echo "[ERROR] Docker Compose (v2) is not installed."
    exit 1
fi

cd "$SCRIPT_DIR"

# .env 파일 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "[WARN] .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "[INFO] Please edit .env and update passwords before production use."
fi

echo "[INFO] Starting all services (PostgreSQL, Redis, Neo4j, MinIO)..."
docker compose --env-file .env up -d

echo ""
echo "[INFO] Waiting for services to be healthy..."
sleep 15

# 상태 확인
echo ""
echo "-- Service Status --"

check_service() {
    local name=$1
    local url=$2
    if curl -sf -o /dev/null -w "" "$url" 2>/dev/null; then
        echo "  [OK] $name"
    else
        echo "  [WAIT] $name (may still be starting...)"
    fi
}

# PostgreSQL 확인
if docker exec narrative-postgres pg_isready -U narative -d narrative_invest &>/dev/null; then
    echo "  [OK] PostgreSQL (port 5432)"
else
    echo "  [WAIT] PostgreSQL (may still be starting...)"
fi

# Redis 확인
if docker exec narrative-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "  [OK] Redis (port 6379)"
else
    echo "  [WAIT] Redis (may still be starting...)"
fi

check_service "Neo4j (port 7474/7687)" "http://localhost:7474"
check_service "MinIO (port 9000/9001)" "http://localhost:9000/minio/health/live"

echo ""
echo "================================================"
echo " Service Information:"
echo "================================================"
echo ""
echo "PostgreSQL:"
echo "  - Host: 10.10.10.10:5432"
echo "  - Database: narrative_invest"
echo "  - Connection: postgresql://narative:password@10.10.10.10:5432/narrative_invest"
echo ""
echo "Redis:"
echo "  - Host: 10.10.10.10:6379"
echo "  - URL: redis://10.10.10.10:6379/0"
echo ""
echo "Neo4j:"
echo "  - Browser: http://10.10.10.10:7474"
echo "  - Bolt URI: bolt://10.10.10.10:7687"
echo ""
echo "MinIO:"
echo "  - API: http://10.10.10.10:9000"
echo "  - Console: http://10.10.10.10:9001"
echo ""
echo "[OK] Infrastructure setup complete!"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f          # 로그 확인"
echo "  docker compose ps               # 상태 확인"
echo "  docker compose down             # 전체 중지"
echo "  docker compose restart neo4j    # 개별 재시작"
