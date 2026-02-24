# Make 명령어 레퍼런스

> 모든 명령어는 프로젝트 루트(`~/adelie-investment`)에서 실행합니다.
> 빠른 시작은 [QUICKSTART.md](../../QUICKSTART.md)를 참고하세요.

---

## Root Makefile (팀원 공통)

### 개발 환경

```bash
make dev                  # 전체 스택 실행 (docker-compose.dev.yml)
make dev-down             # 전체 스택 중지
make dev-frontend         # 프론트엔드만 실행
make dev-api              # 백엔드 API만 실행
make dev-frontend-local   # 프론트엔드 로컬 실행 (Docker 없이, npm run dev)
make dev-api-local        # 백엔드 API 로컬 실행 (Docker 없이, uvicorn)
make status               # 컨테이너 상태 + 현재 브랜치 출력
```

### 테스트

```bash
make test                 # 전체 테스트 (backend pytest)
make test-unit            # 유닛 테스트만 (tests/unit/)
make test-e2e             # Playwright E2E 테스트
make test-load            # Locust 부하 테스트 (40명, 2분)
make test-pipeline        # 파이프라인 검증 테스트
```

### DB

```bash
make migrate              # alembic upgrade heads
make db-reset             # DB 초기화 (⚠️  개발 환경 전용)
make db-sync              # prod DB 콘텐츠 → 로컬 dev DB 복제
```

### 유틸

```bash
make clean                # Docker 캐시 + __pycache__ 정리
make logs                 # 프로덕션 로그 tail
```

### 빌드/배포 (인프라 전용)

```bash
make build                # 전체 Docker 이미지 빌드
make build-frontend       # 프론트엔드만 빌드
make build-api            # 백엔드 API만 빌드
make build-ai             # AI 파이프라인만 빌드
make push                 # Docker Hub push (REGISTRY=dorae222 TAG=latest)
make deploy               # docker-compose.prod.yml up -d (deploy-test에서)
make rollback             # feb20-stable 이미지로 deploy-test 롤백
```

> 변수 오버라이드: `make push REGISTRY=dorae222 TAG=v1.3`

---

## lxd/Makefile (인프라 전용)

```bash
# 실행 방법
make -f lxd/Makefile <target>
```

### LXD 서버 관리

```bash
make -f lxd/Makefile health       # 5대 서버 브랜치 + Docker 컨테이너 상태
make -f lxd/Makefile git-check    # git user/email/remote 설정 점검
make -f lxd/Makefile jwt-fix      # JWT_SECRET 기본값 서버 자동 갱신
make -f lxd/Makefile sync         # 각 서버 git pull + docker compose up -d
make -f lxd/Makefile db-sync      # prod DB 콘텐츠 → 각 서버 로컬 dev DB 복제
```

### 배포

```bash
make -f lxd/Makefile push         # Docker Hub 이미지 push
make -f lxd/Makefile deploy       # deploy-test 전체 배포 (빌드→push→SSH)
make -f lxd/Makefile rollback     # feb20-stable 이미지로 deploy-test 롤백
make -f lxd/Makefile deploy-service SVC=frontend   # 단일 서비스 배포
```

### dev-final 환경

```bash
make -f lxd/Makefile dev-final-setup    # 브랜치 생성 + checkout + 재빌드 (전체)
make -f lxd/Makefile dev-final-sync     # 각 서버 dev-final/* pull + up -d
make -f lxd/Makefile db-local-setup     # 로컬 postgres 기동 + alembic + prod 데이터 복제
```

---

## 시나리오별 명령어

### 처음 개발 환경 세팅할 때

```bash
git pull origin dev-final/<내역할>
make dev
make migrate
```

### 코드 수정 후 빠른 테스트

```bash
make test-unit
```

### 전체 서버 상태가 궁금할 때 (인프라)

```bash
make -f lxd/Makefile health
```

### DB를 새로 받고 싶을 때

```bash
# ⚠️ 기존 데이터 덮어씀 — 팀 공지 후 실행
make -f lxd/Makefile db-local-setup
```

### Docker 이미지가 너무 쌓였을 때

```bash
make clean
```

### deploy-test에 배포하고 싶을 때 (인프라 전용)

```bash
make -f lxd/Makefile deploy
```

### 배포 실패 → 롤백

```bash
make -f lxd/Makefile rollback
```

---

## 하위 호환 별칭 (구 명령어 → 새 명령어)

| 구 명령어 | 새 명령어 |
|----------|---------|
| `make sync-dev-data` | `make db-sync` |
| `make -f lxd/Makefile health-lxd` | `make -f lxd/Makefile health` |
| `make -f lxd/Makefile check-lxd-git` | `make -f lxd/Makefile git-check` |
| `make -f lxd/Makefile fix-lxd-jwt` | `make -f lxd/Makefile jwt-fix` |
| `make -f lxd/Makefile sync-lxd` | `make -f lxd/Makefile sync` |
| `make -f lxd/Makefile sync-dev-data` | `make -f lxd/Makefile db-sync` |
| `make -f lxd/Makefile dev-local-db-setup` | `make -f lxd/Makefile db-local-setup` |
| `make -f lxd/Makefile deploy-test` | `make -f lxd/Makefile deploy` |
| `make -f lxd/Makefile rollback-stable` | `make -f lxd/Makefile rollback` |

구 명령어도 여전히 동작합니다 (별칭으로 유지).
