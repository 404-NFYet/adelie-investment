# Infra 교차 의존성

> 다른 파트 변경이 인프라에 미치는 영향과 대응법을 정리한다.

---

## 1. Dockerfile 변경 시

각 파트에서 Dockerfile을 수정하면 Docker 이미지 빌드와 배포에 영향을 준다.

### Dockerfile 위치 및 빌드 컨텍스트

| 이미지 | Dockerfile | 빌드 컨텍스트 | 파트 담당자 |
|--------|-----------|-------------|-----------|
| `adelie-frontend` | `frontend/Dockerfile` | `./frontend` | 손영진 |
| `adelie-backend-api` | `fastapi/Dockerfile` | `.` (프로젝트 루트) | 허진서 |
| `adelie-ai-pipeline` | `datapipeline/Dockerfile` | `.` (프로젝트 루트) | 안례진 |

### 체크리스트

Dockerfile이 변경될 때:

- [ ] 로컬에서 `docker build` 성공 확인
  ```bash
  # Frontend
  docker build -t test-frontend ./frontend
  # Backend API (컨텍스트가 프로젝트 루트)
  docker build -t test-api -f fastapi/Dockerfile .
  # Pipeline
  docker build -t test-pipeline -f datapipeline/Dockerfile .
  ```
- [ ] `docker-compose.dev.yml`에서 빌드 + 실행 테스트
  ```bash
  docker compose -f docker-compose.dev.yml build <서비스명>
  docker compose -f docker-compose.dev.yml up <서비스명>
  ```
- [ ] `docker-compose.prod.yml`의 이미지 이름/빌드 설정과 일치하는지 확인
- [ ] PR에 `[영향: Infra]` 태그 + 도형준 리뷰어 추가

### Backend Dockerfile 특이사항

`fastapi/Dockerfile`은 빌드 컨텍스트가 프로젝트 루트(`.`)이다. `chatbot/`, `datapipeline/` 모듈을 같은 이미지에 포함하기 때문이다.

```dockerfile
COPY fastapi/ /app/fastapi/
COPY chatbot/ /app/chatbot/
COPY datapipeline/ /app/datapipeline/
```

`chatbot/requirements.txt` 변경 시에도 Backend Dockerfile 재빌드가 필요하다.

---

## 2. 환경변수 추가/변경 시

### 체크리스트

새 환경변수가 필요할 때:

- [ ] `.env.example` 업데이트 (기본값 + 설명)
- [ ] 다음 파일들에서 해당 변수가 전달되는지 확인:

| 파일 | 확인 사항 |
|------|----------|
| `docker-compose.dev.yml` | `env_file: .env` 또는 `environment:` 섹션 |
| `docker-compose.prod.yml` | `env_file: .env` 또는 `environment:` 섹션 |
| `docker-compose.test.yml` | 테스트 환경 변수 |

- [ ] deploy-test 서버의 `.env` 파일 동기화
  ```bash
  ssh deploy-test 'cat ~/adelie-investment/.env'
  # 누락된 변수 추가
  ```
- [ ] Discord #infra 채널에 변수 추가 알림

### 환경변수 분류

| 카테고리 | 변수 예시 | 관리자 |
|---------|----------|--------|
| DB 연결 | `DATABASE_URL`, `REDIS_URL` | Infra |
| API 키 | `OPENAI_API_KEY`, `PERPLEXITY_API_KEY` | Pipeline / Backend |
| JWT 인증 | `JWT_SECRET` | Backend |
| CORS | `CORS_ALLOWED_ORIGINS` | Backend |
| 파이프라인 모델 | `DEFAULT_MODEL`, `CHART_MODEL` | Pipeline |
| MinIO | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY` | Infra |

---

## 3. requirements.txt 변경 시

### 체크리스트

Python 패키지가 추가/변경/삭제될 때:

- [ ] 해당 Dockerfile에서 `pip install -r requirements.txt`가 실행되는지 확인
- [ ] Docker 이미지 재빌드 필수
  ```bash
  docker compose -f docker-compose.dev.yml build <서비스명>
  ```
- [ ] 패키지 버전 충돌 확인
  - `fastapi/requirements.txt`와 `datapipeline/requirements.txt`가 같은 이미지에 포함될 때 버전 충돌 가능
  - Backend Dockerfile에서 두 requirements.txt를 순서대로 설치하므로 후자가 우선
- [ ] `docker-compose.dev.yml`의 `develop.watch` 설정 확인
  ```yaml
  develop:
    watch:
      - action: rebuild
        path: ./fastapi/requirements.txt   # requirements 변경 시 rebuild
  ```

### requirements.txt 위치

| 파일 | Dockerfile | 비고 |
|------|-----------|------|
| `fastapi/requirements.txt` | `fastapi/Dockerfile` | Backend + Chatbot + Pipeline 공용 이미지 |
| `datapipeline/requirements.txt` | `datapipeline/Dockerfile` | Pipeline 전용 이미지 (별도) |
| `frontend/package.json` | `frontend/Dockerfile` | Node.js 의존성 |

---

## 4. DB 스키마 변경 시

### 체크리스트

Alembic migration이 추가될 때:

- [ ] 로컬에서 migration 적용 + 롤백 테스트
  ```bash
  cd database && ../.venv/bin/alembic upgrade head
  cd database && ../.venv/bin/alembic downgrade -1
  cd database && ../.venv/bin/alembic upgrade head
  ```
- [ ] Docker dev 환경에서 migration 적용
  ```bash
  docker compose -f docker-compose.dev.yml run db-migrate
  ```
- [ ] deploy-test에서 migration 적용
  ```bash
  ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'
  ```
- [ ] migration 전후 데이터 무결성 확인
  ```bash
  ssh deploy-test 'docker exec adelie-postgres psql -U narative -d narrative_invest -c "\dt"'
  ```

### 위험한 migration 유형

| 유형 | 위험도 | 대응 |
|------|--------|------|
| 컬럼 추가 (NOT NULL + DEFAULT) | 낮음 | 자동 적용 가능 |
| 컬럼 추가 (NOT NULL, DEFAULT 없음) | 높음 | 기존 데이터 마이그레이션 필요 |
| 컬럼 삭제/리네임 | 높음 | Pipeline writer.py, Backend route 사전 수정 필요 |
| 테이블 삭제 | 매우 높음 | 백업 후 진행, 모든 파트 사전 확인 |
| 인덱스 추가 | 낮음 | 대용량 테이블은 CONCURRENTLY 옵션 |

---

## 5. docker-compose 변경 시 (Infra → 다른 파트)

### 체크리스트

docker-compose 파일을 변경할 때:

- [ ] Discord #infra 채널에 변경 내용 공지
- [ ] 서비스 포트 변경 시:
  - [ ] Frontend `vite.config.js` proxy 설정 확인 (`localhost:8082`)
  - [ ] Backend `app/core/config.py` DATABASE_URL/REDIS_URL 기본값 확인
  - [ ] Pipeline `datapipeline/config.py` 환경변수 확인
- [ ] 서비스명 변경 시:
  - [ ] `docker-compose.dev.yml`, `docker-compose.prod.yml`, `docker-compose.test.yml` 모두 동기화
  - [ ] nginx 설정(`frontend/nginx.conf`)의 upstream 이름 확인
- [ ] 환경변수 변경 시:
  - [ ] `.env.example` 업데이트
  - [ ] 팀원들에게 `.env` 파일 업데이트 안내
- [ ] 변경 후 팀원들이 수행해야 할 명령어 안내
  ```bash
  docker compose -f docker-compose.dev.yml down
  docker compose -f docker-compose.dev.yml pull  # (이미지 변경 시)
  docker compose -f docker-compose.dev.yml up -d
  ```

---

## 6. Frontend nginx 설정 변경 시

Frontend 이미지(`frontend/Dockerfile`)에 nginx가 포함되어 있다.

### 확인 사항

- [ ] `/api/v1/*` → `backend-api:8082` 프록시 설정 유지
- [ ] `/api/auth/*` → `/api/v1/auth/*` 리라이트 규칙 유지
- [ ] SPA 폴백 (`try_files $uri /index.html`) 유지
- [ ] 새 정적 경로 추가 시 nginx location 블록 추가 필요 여부

---

## 7. 영향 요약 매트릭스

| 변경 주체 | Infra 확인 사항 |
|-----------|----------------|
| Frontend | Dockerfile 변경 → 이미지 재빌드, nginx.conf 변경 → 프록시 확인 |
| Backend | Dockerfile 변경 → 이미지 재빌드, requirements.txt → 패키지 충돌 확인 |
| Chatbot | requirements.txt → Backend Dockerfile 재빌드 (같은 이미지) |
| Pipeline | Dockerfile 변경 → 이미지 재빌드, 환경변수 추가 → .env + compose 확인 |
| Database | migration 추가 → deploy-test 적용 필요 |
