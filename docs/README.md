# 아델리에 - 문서 가이드

## 읽기 순서

| # | 문서 | 대상 | 설명 |
|---|------|------|------|
| 1 | [01_SETUP.md](01_SETUP.md) | 신규 팀원 | LXD 접속, 프로젝트 클론, 환경 변수, 데이터 초기화 |
| 2 | [02_DOCKER.md](02_DOCKER.md) | 전체 팀원 | Docker Compose 3종 사용법, 개발 워크플로우, 트러블슈팅 |
| 3 | [03_DEPLOYMENT.md](03_DEPLOYMENT.md) | 배포 담당 | deploy-test 배포, Cloudflare Tunnel, AWS Terraform |
| 4 | [04_TESTING.md](04_TESTING.md) | 개발자 | pytest, Playwright E2E, 부하 테스트 |
| 5 | [05_AI_PIPELINE.md](05_AI_PIPELINE.md) | AI 담당 | 데이터 수집, 키워드 생성, 역사적 사례 매칭, 프롬프트 관리 |
| 6 | [06_CONTRIBUTING.md](06_CONTRIBUTING.md) | 전체 팀원 | Git 전략, 커밋 컨벤션, PR 워크플로우, 릴리스 프로세스, 모노레포 구조 |
| 7 | [07_CHANGELOG.md](07_CHANGELOG.md) | 전체 팀원 | 날짜별 변경 이력 (버그 수정, 기능, UI, 인프라) |
| 8 | [08_SCHEDULER.md](08_SCHEDULER.md) | 백엔드/배포 | 데일리 파이프라인 스케줄러 (APScheduler, KST 08:00) |
| 9 | [09_LEADERBOARD.md](09_LEADERBOARD.md) | 프론트/백엔드 | 수익률 리더보드 API 스펙 + 컴포넌트 구조 |

## 참고 문서

| 문서 | 설명 |
|------|------|
| [PRD.md](PRD.md) | 제품 요구사항 명세서 |
| [FEEDBACK.md](FEEDBACK.md) | 피드백 프로세스 |
| [aws/](aws/) | AWS 배포 가이드 (01~11번 순서) |
| [database/](database/) | DB 스키마 (DBML) |

## 빠른 시작 (5분)

```bash
# 1. LXD 컨테이너 접속
ssh ubuntu@10.10.10.{번호}

# 2. 프로젝트 클론 + 환경변수 설정
cd ~ && git clone https://github.com/404-NFYet/adelie-investment.git
cd adelie-investment && cp .env.example .env
# → .env 파일에 OPENAI_API_KEY 입력 (팀장에게 요청)

# 3. 개발 서버 실행
make dev

# 4. 접속
# 프론트엔드: http://localhost:3001
# FastAPI Docs: http://localhost:8082/docs
```

상세 내용은 [01_SETUP.md](01_SETUP.md)를 참조하세요.
