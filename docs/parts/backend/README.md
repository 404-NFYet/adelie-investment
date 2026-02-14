# Backend 개발 가이드 — 허진서

## 환경 정보

| 항목 | 값 |
|------|-----|
| 컨테이너 | dev-jjjh02 (10.10.10.12) |
| 리소스 | 4 CPU / 8GB RAM / 150GB Disk |
| 브랜치 | `dev/backend` |
| Git | jjjh02 <jinnyshur0104@gmail.com> |
| SSH | `ssh dev-jjjh02` (ProxyJump: hj-server) |

## 환경 확인 체크리스트

- [ ] SSH 접속 확인: `ssh dev-jjjh02`
- [ ] 브랜치: `git branch --show-current` → `dev/backend`
- [ ] .env 확인: `grep DATABASE_URL .env | head -c50`
- [ ] Docker: `docker ps` → adelie-postgres, adelie-redis 실행 중
- [ ] 서버 실행: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload` (fastapi/ 디렉토리에서)
- [ ] Swagger UI: `http://localhost:8082/docs`
- [ ] 헬스 체크: `curl http://localhost:8082/api/v1/health`

## 주요 명령어

| 작업 | 명령어 |
|------|--------|
| 로컬 서버 실행 | `cd fastapi && ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload` |
| Docker 서버 실행 | `make dev-api` |
| 단위 테스트 | `.venv/bin/pytest tests/unit/ -v` |
| 백엔드 통합 테스트 | `.venv/bin/pytest tests/backend/ -v` |
| Alembic migration 생성 | `cd database && ../.venv/bin/alembic revision --autogenerate -m "설명"` |
| Alembic migration 적용 | `cd database && ../.venv/bin/alembic upgrade head` |
| 현재 migration 확인 | `cd database && ../.venv/bin/alembic current` |
| Swagger UI | `http://localhost:8082/docs` |

## 개발 워크플로우

1. `dev/backend`에서 작업 → 커밋 (`type: 한글 설명`) → push
2. develop으로 PR → 최소 1명 리뷰 → squash merge
3. 커밋 전: `git config user.name` = `jjjh02` 확인
4. DB 스키마 변경 시: Alembic migration 생성 → PR에 migration 파일 포함

## 이 폴더의 문서

- [architecture.md](architecture.md) — FastAPI 앱 구조, 라우터, JWT 인증, 모델, Alembic
- [roadmap.md](roadmap.md) — P0/P1/P2 개선 과제
- [dependencies.md](dependencies.md) — DB 스키마 변경 체크리스트, Chatbot/Pipeline 연동
