# Narrative Investment - Infrastructure Setup

## 개요

infra-server (10.10.10.10)에서 실행되는 모든 인프라 서비스를 하나의 `docker-compose.yml`로 통합 관리합니다.

**포함 서비스 (4개)**:
- PostgreSQL 16 + pgvector (메인 DB)
- Redis 7 (캐싱, 세션, Rate Limiting)
- Neo4j 5 Community (기업 관계 그래프 DB)
- MinIO (S3 호환 오브젝트 스토리지)

## 사전 조건

- Docker 및 Docker Compose 설치
- infra-server (10.10.10.10) SSH 접근 권한

## 서비스 구성

```
docker-compose.yml (통합)
├── postgres    (pgvector/pgvector:pg16)    :5432
├── redis       (redis:7-alpine)            :6379
├── neo4j       (neo4j:5-community)         :7474, :7687
└── minio       (minio/minio:latest)        :9000, :9001
```

모든 서비스는 `narrative-network` 네트워크에서 통신합니다.

## 설치 방법

### 1. 파일 복사

```bash
# 로컬에서 실행
scp -r /home/hj/2026/project/narrative-investment/infra/* root@10.10.10.10:/opt/narrative-investment/infra/
```

### 2. 환경 변수 설정

```bash
# infra-server에서 실행
cd /opt/narrative-investment/infra
cp .env.example .env
# 필요 시 .env 파일에서 비밀번호 등 수정
```

### 3. 컨테이너 시작

```bash
# 셋업 스크립트로 실행
cd /opt/narrative-investment/infra
chmod +x setup-infra.sh
./setup-infra.sh
```

또는 직접 docker-compose 실행:

```bash
cd /opt/narrative-investment/infra
docker compose --env-file .env up -d
```

## 서비스 정보

### PostgreSQL 16 + pgvector

| 항목 | 값 |
|------|------|
| Image | `pgvector/pgvector:pg16` |
| Container | `narrative-postgres` |
| Port | 5432 |
| Database | narrative_invest |
| Username | narative |
| Password | password |
| Memory Limit | 4G |
| 용도 | 메인 DB, 벡터 검색 (pgvector), 주가/사례/스토리 저장 |

### Redis 7

| 항목 | 값 |
|------|------|
| Image | `redis:7-alpine` |
| Container | `narrative-redis` |
| Port | 6379 |
| Max Memory | 512MB (allkeys-lru 정책) |
| Persistence | AOF (appendonly) |
| Memory Limit | 1G |
| 용도 | 세션 캐싱, 브리핑 캐시 (TTL: 6시간), Rate Limiting |

### Neo4j 5 Community (Graph Database)

| 항목 | 값 |
|------|------|
| Image | `neo4j:5-community` |
| Container | `narrative-neo4j` |
| Browser URL | http://10.10.10.10:7474 |
| Bolt URI | bolt://10.10.10.10:7687 |
| Username | neo4j |
| Password | password |
| Plugins | APOC |
| Heap | 512MB ~ 2G |
| Memory Limit | 4G |
| 용도 | 기업 관계 그래프 (공급망, 경쟁사, 계열사) |

### MinIO (S3-compatible Storage)

| 항목 | 값 |
|------|------|
| Image | `minio/minio:latest` |
| Container | `narrative-minio` |
| API URL | http://10.10.10.10:9000 |
| Console URL | http://10.10.10.10:9001 |
| Username | minioadmin |
| Password | minioadmin123 |
| Memory Limit | 1G |
| 용도 | 증권사 리포트 PDF 저장, 추출 데이터 저장 |

## 버킷 생성 (MinIO)

MinIO Console (http://10.10.10.10:9001)에서 로그인 후 생성:

| 버킷명 | 용도 |
|--------|------|
| `naver-reports` | 네이버 증권사 리포트 PDF 저장 |
| `extracted-data` | Vision API로 추출한 데이터 저장 |

## 리소스 요약

| 서비스 | Memory Limit | CPU Limit |
|--------|-------------|-----------|
| PostgreSQL | 4G | 4 cores |
| Redis | 1G | 1 core |
| Neo4j | 4G | 2 cores |
| MinIO | 1G | 1 core |
| **합계** | **10G** | **8 cores** |

## 볼륨

| 볼륨명 | 서비스 | 컨테이너 경로 |
|--------|--------|--------------|
| `postgres_data` | PostgreSQL | /var/lib/postgresql/data |
| `redis_data` | Redis | /data |
| `neo4j_data` | Neo4j | /data |
| `neo4j_logs` | Neo4j | /logs |
| `neo4j_import` | Neo4j | /var/lib/neo4j/import |
| `minio_data` | MinIO | /data |

## 상태 확인

```bash
# 전체 서비스 상태
docker compose ps

# 개별 서비스 헬스체크
# PostgreSQL
docker exec narrative-postgres pg_isready -U narative -d narrative_invest

# Redis
docker exec narrative-redis redis-cli ping

# Neo4j
curl http://10.10.10.10:7474

# MinIO
curl http://10.10.10.10:9000/minio/health/live
```

## 문제 해결

### 컨테이너 로그 확인

```bash
docker logs narrative-postgres
docker logs narrative-redis
docker logs narrative-neo4j
docker logs narrative-minio
```

### 개별 서비스 재시작

```bash
docker compose restart postgres
docker compose restart redis
docker compose restart neo4j
docker compose restart minio
```

### 전체 서비스 재시작

```bash
cd /opt/narrative-investment/infra
docker compose down
docker compose --env-file .env up -d
```

### 데이터 초기화 (주의: 데이터 삭제됨)

```bash
docker compose down -v    # 볼륨 포함 삭제
docker compose --env-file .env up -d
```

## 백업

`backup.sh` 스크립트를 사용하여 데이터를 백업할 수 있습니다:

```bash
chmod +x backup.sh
./backup.sh
```
