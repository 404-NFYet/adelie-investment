# Infra 개발 가이드 — 도형준

## 환경 정보

| 항목 | 값 |
|------|-----|
| 컨테이너 | dev-hj (10.10.10.15) |
| 리소스 | 4 CPU / 8GB RAM / 150GB Disk |
| 브랜치 | `dev/infra` |
| Git | dorae222 <dhj9842@gmail.com> |
| SSH | `ssh dev-hj` (ProxyJump: hj-server) |

## 관리 대상 서버

| 서버 | IP | 역할 | SSH |
|------|-----|------|-----|
| infra-server | 10.10.10.10 | 공유 인프라 (PostgreSQL, Redis, MinIO, Prometheus, Grafana) | `ssh infra-server` |
| deploy-test | 10.10.10.20 | 프로덕션 배포 서버 | `ssh deploy-test` |
| dev-* (5개) | 10.10.10.11~15 | 팀원별 개발 환경 | `ssh dev-{name}` |

## 환경 확인 체크리스트

- [ ] SSH 접속: `ssh dev-hj`, `ssh infra-server`, `ssh deploy-test`
- [ ] 브랜치: `git branch --show-current` → `dev/infra`
- [ ] deploy-test Docker: `ssh deploy-test 'docker ps'` → adelie-* 컨테이너 실행 중
- [ ] Grafana: https://monitoring.adelie-invest.com (mutsa1234/mutsa1234)
- [ ] Prometheus: `ssh infra-server 'curl -s http://localhost:9090/api/v1/targets | jq .data.activeTargets[].health'`

## 주요 명령어

| 작업 | 명령어 |
|------|--------|
| 전체 빌드 | `make build` |
| 프론트엔드만 빌드 | `make build-frontend` |
| 백엔드 API만 빌드 | `make build-api` |
| Docker Hub 푸시 | `make push` |
| deploy-test 배포 | `make deploy` |
| deploy-test DB 마이그레이션 | `ssh deploy-test 'docker exec adelie-backend-api sh -c "cd /app/database && alembic upgrade head"'` |
| 모니터링 재시작 | `ssh infra-server 'cd /opt/narrative-investment/infra/monitoring && docker compose restart'` |

## 개발 워크플로우

1. `dev/infra`에서 작업 → 커밋 (`type: 한글 설명`) → push
2. develop으로 PR → 최소 1명 리뷰 → squash merge
3. 커밋 전: `git config user.name` = `dorae222` 확인
4. docker-compose 변경 시: Discord #infra에 공지 필수

## 이 폴더의 문서

- [architecture.md](architecture.md) — LXD 인스턴스, Docker Compose, Cloudflare Tunnel, GitHub Actions
- [monitoring.md](monitoring.md) — Grafana + Prometheus 구성, 알림 규칙
- [roadmap.md](roadmap.md) — P0/P1/P2 개선 과제
- [dependencies.md](dependencies.md) — Dockerfile/환경변수/requirements 변경 대응
