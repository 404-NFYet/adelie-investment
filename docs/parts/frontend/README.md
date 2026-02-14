# Frontend 개발 가이드 — 손영진

## 환경 정보
| 항목 | 값 |
|------|-----|
| 컨테이너 | dev-yj99son (10.10.10.14) |
| 리소스 | 4 CPU / 8GB RAM / 150GB Disk |
| 브랜치 | `dev/frontend` |
| Git | YJ99Son <syjin2008@naver.com> |
| SSH | `ssh dev-yj99son` (ProxyJump: hj-server) |

## 환경 확인 체크리스트
- [ ] SSH 접속 확인: `ssh dev-yj99son`
- [ ] 브랜치: `git branch --show-current` → `dev/frontend`
- [ ] .env API 키: `grep OPENAI_API_KEY .env | head -c30`
- [ ] Docker: `docker ps` → adelie-postgres, adelie-redis 실행 중
- [ ] 프론트 실행: `cd frontend && npm run dev` → http://10.10.10.14:3001
- [ ] 백엔드 실행: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8082`
- [ ] API 연결: 브라우저에서 키워드 카드 로딩 확인

## 주요 명령어
| 작업 | 명령어 |
|------|--------|
| 개발 서버 | `cd frontend && npm run dev` |
| 프로덕션 빌드 | `cd frontend && npm run build` |
| Docker 빌드 | `docker build -t dorae222/adelie-frontend:dev-$(git rev-parse --short HEAD) -f frontend/Dockerfile .` |
| 린트 | `cd frontend && npm run lint` |
| 전체 스택 (Docker) | `docker compose -f docker-compose.dev.yml up` |

## 개발 워크플로우
1. `dev/frontend`에서 작업 → 커밋 (`type: 한글 설명`) → push
2. develop으로 PR → 최소 1명 리뷰 → squash merge
3. 커밋 전: `git config user.name` = `YJ99Son` 확인

## 이 폴더의 문서
- [architecture.md](architecture.md) — 디렉토리 구조, 라우팅, 컨텍스트, API 레이어
- [local-dev.md](local-dev.md) — 로컬 개발 상세 (포트, 프록시, 디버깅)
- [roadmap.md](roadmap.md) — P0/P1/P2 개선 과제
- [dependencies.md](dependencies.md) — 다른 파트 변경 시 대응법
