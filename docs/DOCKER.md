# Docker 워크플로우 가이드

## Docker Compose 파일 구조

| 파일 | 용도 | DB 연결 |
|------|------|---------|
| `docker-compose.dev.yml` | 개발자 로컬 개발 | infra-server (10.10.10.10) 공유 |
| `docker-compose.prod.yml` | deploy-test / AWS 배포 | 자체 포함 (풀스택) |
| `docker-compose.test.yml` | 자동화 테스트 | 격리된 테스트 DB |

## Makefile 명령어

```bash
make help           # 전체 명령어 확인
make build          # 4개 서비스 Docker 이미지 빌드
make build TAG=v1.0 # 태그 지정 빌드
make push           # Docker Hub (dorae222/*) 푸시
make push-local     # 로컬 레지스트리 (10.10.10.10:5000) 푸시
make dev            # 개발 환경 실행
make deploy         # 배포 환경 실행
make test           # 테스트 실행
make logs           # 로그 조회
make clean          # 정리
```

## 이미지 네이밍

| 서비스 | Docker Hub 이미지 |
|--------|------------------|
| Frontend | `dorae222/adelie-frontend:TAG` |
| FastAPI | `dorae222/adelie-backend-api:TAG` |
| Spring Boot | `dorae222/adelie-backend-spring:TAG` |
| AI Pipeline | `dorae222/adelie-ai-pipeline:TAG` |

## 개발 -> 배포 플로우

```
1. 코드 수정 (dev 컨테이너)
   ↓
2. make dev로 로컬 테스트
   ↓
3. git commit & push
   ↓
4. make build TAG=v1.1
   ↓
5. make push TAG=v1.1
   ↓
6. deploy-test에서:
   REGISTRY=dorae222 TAG=v1.1 docker compose -f docker-compose.prod.yml up -d
   ↓
7. 데이터 초기화 (필요 시):
   docker exec -e OPENAI_API_KEY="$KEY" adelie-backend-api python /app/generate_cases.py
```

## 핫 리로드 (개발 환경)

`docker-compose.dev.yml`에서 FastAPI는 `--reload` 모드로 실행됩니다.
`backend_api/app/` 디렉토리의 파일 변경 시 자동 재시작됩니다.

## 트러블슈팅

### 빌드 캐시 문제
```bash
docker compose -f docker-compose.dev.yml build --no-cache
```

### 컨테이너 로그 확인
```bash
docker compose -f docker-compose.dev.yml logs backend-api -f
```

### 특정 서비스 재시작
```bash
docker compose -f docker-compose.dev.yml restart backend-api
```
