"""대시보드 설정 — 서버 정보, DB 연결 상수"""

import os

# 팀원별 개발 서버
SERVERS = {
    "손영진 (프론트엔드)": {
        "host": "10.10.10.14",
        "ssh_alias": "dev-yj99son",
        "role": "frontend",
        "port_api": 8082,
        "port_front": 3001,
    },
    "정지훈 (챗봇)": {
        "host": "10.10.10.11",
        "ssh_alias": "dev-j2hoon10",
        "role": "chatbot",
        "port_api": 8082,
        "port_front": 3001,
    },
    "허진서 (백엔드)": {
        "host": "10.10.10.12",
        "ssh_alias": "dev-jjjh02",
        "role": "backend",
        "port_api": 8082,
        "port_front": 3001,
    },
    "안례진 (파이프라인)": {
        "host": "10.10.10.13",
        "ssh_alias": "dev-ryejinn",
        "role": "pipeline",
        "port_api": 8082,
        "port_front": 3001,
    },
    "도형준 (인프라)": {
        "host": "10.10.10.15",
        "ssh_alias": "dev-hj",
        "role": "infra",
        "port_api": 8082,
        "port_front": 3001,
    },
}

# deploy-test 서버
DEPLOY_SERVER = {
    "host": "10.10.10.20",
    "ssh_alias": "deploy-test",
    "port_api": 8082,
    "port_front": 80,
}

# DB 설정 (deploy-test의 PostgreSQL — infra-server에서도 직접 접근 가능)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "10.10.10.10"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "narrative_invest"),
    "user": os.getenv("DB_USER", "narative"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

# SSH 설정
SSH_USER = "ubuntu"
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "/root/.ssh/id_ed25519")

# 프로젝트 디렉토리 (각 서버 내)
PROJECT_DIR = "~/adelie-investment"

# 포트 및 엔드포인트 상수
HEALTH_CHECK_ENDPOINT = "/api/v1/health"
COMPOSE_FILE_DEV = "docker-compose.dev.yml"
COMPOSE_FILE_PROD = "docker-compose.prod.yml"
REDIS_CONTAINER_FILTER = "name=redis"
POSTGRES_CONTAINER_FILTER = "name=postgres"

# Prometheus 설정
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://10.10.10.10:9090")

# Grafana 설정
GRAFANA_URL = os.getenv("GRAFANA_URL", "https://monitoring.adelie-invest.com")
