# 브랜치 전략 & 개발 워크플로우

> **마지막 업데이트: 2026-02-24** | 기준 브랜치: `prod-final` (77921fe)

---

## 브랜치 구조

```
prod-final                          ← 프로덕션 (deploy-test 배포 기준)
  ├── dev-final/frontend            ← 손영진 (React UI)
  ├── dev-final/chatbot             ← 정지훈 (AI 개발)
  ├── dev-final/pipeline            ← 안례진 (파이프라인 QA)
  ├── dev-final/backend             ← 허진서 (백엔드)
  └── dev-final/infra               ← 도형준 (인프라)
```

### 핵심 원칙

- **모든 환경은 코드 동일** — 브랜치명만 다름
- 유일한 예외: `dev-final/pipeline`은 prod-final + 례진 고유 커밋(들)
- `main`, `develop` 브랜치는 **미사용** (레거시)
- `:latest` Docker 태그 **사용 중지** → `prod-YYYYMMDD` 명시적 태그만

---

## 담당자 & 브랜치 매핑

| 담당자 | git user.name | git user.email | LXD 서버 | 브랜치 |
|--------|--------------|----------------|----------|--------|
| 손영진 (프론트) | YJ99Son | syjin2008@naver.com | dev-yj99son | `dev-final/frontend` |
| 정지훈 (챗봇) | J2hoon10 | myhome559755@naver.com | dev-j2hoon10 | `dev-final/chatbot` |
| 안례진 (파이프라인) | ryejinn | arj1018@ewhain.net | dev-ryejinn | `dev-final/pipeline` |
| 허진서 (백엔드) | jjjh02 | jinnyshur0104@gmail.com | dev-jjjh02 | `dev-final/backend` |
| 도형준 (인프라) | dorae222 | dhj9842@gmail.com | dev-hj | `dev-final/infra` |

---

## 일상 개발 사이클

### 1. 하루 시작 — 최신 코드 pull

```bash
# LXD 서버에서 (예: dev-yj99son)
cd ~/adelie-investment
git pull origin dev-final/frontend

# Docker 서비스 시작
docker compose -f docker-compose.dev.yml up -d
```

### 2. 코드 수정 & 테스트

```bash
# 프론트엔드: http://localhost:3001 (HMR 자동 반영)
# 백엔드 API: http://localhost:8082/docs (uvicorn 자동 재시작)

# 테스트
make test                           # 백엔드 유닛 테스트
pytest tests/test_foo.py -v         # 특정 테스트
```

### 3. 커밋 & push

```bash
# git config 확인 (자신의 계정인지)
git config user.name    # 예: YJ99Son
git config user.email   # 예: syjin2008@naver.com

# 논리적 단위로 분리 커밋
git add frontend/src/pages/HomePage.jsx
git commit -m "feat: 홈페이지 키워드 카드 레이아웃 개선"

git add frontend/src/components/common/Button.jsx
git commit -m "refactor: 공통 버튼 컴포넌트 스타일 통일"

# push
git push origin dev-final/frontend
```

---

## 코드 동기화 흐름

### 방향 1: prod-final → dev-final/* (인프라 담당자가 실행)

**공통 수정(로그, 설정 등)을 prod-final에 커밋한 후 전 브랜치에 배포하는 흐름.**

```bash
# 1. prod-final에서 작업 & 커밋
git checkout prod-final
# ... 수정 & 커밋 ...
git push origin prod-final

# 2. 모든 dev-final/* 브랜치에 merge & push
make -f lxd/Makefile sync-dev-branches

# 3. LXD 5대 서버에서 git pull
make -f lxd/Makefile sync-lxd

# 4. (선택) 한 번에 전부
make -f lxd/Makefile sync-all
```

### 방향 2: dev-final/* → prod-final (PR 머지)

**팀원의 기능 개발 완료 후 prod-final에 통합하는 흐름.**

```bash
# 1. 팀원이 dev-final/* 브랜치에 push 완료

# 2. GitHub에서 PR 생성
#    Base: prod-final  ←  Compare: dev-final/frontend
gh pr create --base prod-final --head dev-final/frontend \
  --title "[Frontend] 키워드 카드 즐겨찾기 기능 추가" \
  --body "## 변경사항\n- ..."

# 3. 리뷰 & Approve (최소 1명)

# 4. Merge (GitHub 웹 또는 CLI)
gh pr merge <PR번호> --merge

# 5. 머지 후 다른 dev-final/* 브랜치에도 반영
make -f lxd/Makefile sync-dev-branches
make -f lxd/Makefile sync-lxd
```

### 방향 3: deploy-test DB → LXD 데이터 동기화

**프로덕션 콘텐츠 데이터를 개발 서버에 복제하는 흐름.**

```bash
# 전체 5대
make -f lxd/Makefile sync-dev-data

# 단일 서버
make -f lxd/Makefile sync-dev-data SERVER=dev-ryejinn
```

대상 테이블 (13개): stock_listings, market_daily_history, stock_daily_history, glossary, company_relations, broker_reports, daily_briefings, daily_narratives, historical_cases, briefing_stocks, narrative_scenarios, case_stock_relations, case_matches

---

## PR (Pull Request) 규칙

### PR 생성

```
Base: prod-final  ←  Compare: dev-final/{파트}
```

- **항상 `prod-final`으로 머지** (`main`, `develop` 아님)
- PR 전에 `prod-final` 최신 코드를 내 브랜치에 반영해둘 것

```bash
# prod-final 최신 반영 후 PR
git fetch origin prod-final
git merge origin/prod-final
# 충돌 해결 후
git push origin dev-final/frontend
```

### PR 제목 형식

```
[파트] 주요 변경사항 요약

예시:
[Frontend] 키워드 카드 즐겨찾기 기능 추가
[Backend] 알림 API 엔드포인트 구현
[Chatbot] 튜터 에이전트 프롬프트 개선
[Pipeline] 뉴스 크롤러 네이버 금융 연동
[Infra] Docker 이미지 빌드 최적화
```

### PR 본문 템플릿

```markdown
## 변경사항
- (구체적으로 무엇을 변경했는지)

## 테스트
- [ ] 로컬 환경에서 기능 동작 확인
- [ ] 관련 유닛 테스트 작성/통과
- [ ] E2E 테스트 통과 (해당 시)

## 스크린샷
(UI 변경 시 첨부)
```

### 리뷰 & 머지

1. PR 생성 → Discord/Slack으로 리뷰 요청
2. 최소 **1명 Approve** 필요
3. 머지 방식: **Merge commit** (Squash 아님 — 커밋 이력 보존)
4. 머지 후: `sync-dev-branches` → `sync-lxd` 실행하여 전 환경 동기화

---

## deploy-test 배포

```bash
# 방법 1: 전체 자동화 (빌드 + push + 원격 배포)
TAG=prod-20260224 make -f lxd/Makefile deploy-test

# 방법 2: 수동 단계별
TAG=prod-20260224 make build-api                      # 로컬 빌드
docker push dorae222/adelie-backend-api:prod-20260224  # Docker Hub push
ssh deploy-test 'cd ~/adelie-investment && git pull origin prod-final'
ssh deploy-test 'cd ~/adelie-investment && TAG=prod-20260224 docker compose -f docker-compose.prod.yml pull backend-api'
ssh deploy-test 'cd ~/adelie-investment && TAG=prod-20260224 docker compose -f docker-compose.prod.yml up -d backend-api'

# 헬스 체크
ssh deploy-test 'curl -s http://localhost:8082/api/v1/health'
```

---

## 커밋 컨벤션

### 메시지 형식

```
type: 한글 설명
```

| Type | 용도 | 예시 |
|------|------|------|
| feat | 새로운 기능 | `feat: 키워드 카드 즐겨찾기 기능 추가` |
| fix | 버그 수정 | `fix: 로그인 토큰 만료 처리 버그 수정` |
| refactor | 리팩토링 (기능 변경 없음) | `refactor: API 클라이언트 에러 핸들링 개선` |
| chore | 빌드/설정 | `chore: Docker 이미지 태그 정책 변경` |
| docs | 문서 | `docs: API 문서에 인증 엔드포인트 설명 추가` |
| test | 테스트 | `test: 포트폴리오 API 통합 테스트 작성` |
| style | 코드 스타일 (포맷팅) | `style: ESLint 규칙 적용` |
| perf | 성능 개선 | `perf: Redis 캐싱으로 API 응답 속도 개선` |

### 커밋 전 체크리스트

```bash
# 1. git config가 본인 계정인지 확인
git config user.name
git config user.email

# 2. 논리적 단위로 분리 (한 번에 몰아서 커밋 금지)
# 나쁜 예: 모델 + 라우트 + 프론트 + 테스트 한 커밋
# 좋은 예: 각각 별도 커밋

# 3. push까지 한 세트
git push origin dev-final/{파트}
```

### 금지 사항

- Co-Authored-By 태그 **절대 금지** (AI 도구 흔적 남기지 않음)
- `--no-verify`, `--force` 플래그 사용 금지
- `prod-final`에 force push **절대 금지**
- 100개 파일 이상 한 커밋 금지 (논리적으로 분리)

---

## 긴급 핫픽스

```bash
# 1. prod-final에서 hotfix 브랜치 생성
git checkout prod-final
git pull origin prod-final
git checkout -b hotfix/fix-critical-bug

# 2. 수정 & 테스트
# ...
make test

# 3. 커밋 & PR
git push origin hotfix/fix-critical-bug
# GitHub PR: Base: prod-final ← Compare: hotfix/fix-critical-bug

# 4. 머지 후 전 환경 동기화
make -f lxd/Makefile sync-dev-branches
make -f lxd/Makefile sync-lxd
```

---

## 인프라 명령 요약 (make -f lxd/Makefile)

| 명령 | 설명 |
|------|------|
| `sync-dev-branches` | prod-final → dev-final/* 5개 브랜치 merge & push |
| `sync-lxd` | LXD 5대 서버에서 각자 브랜치 git pull |
| `sync-all` | 위 두 작업 순차 실행 |
| `sync-dev-data` | deploy-test → LXD DB 콘텐츠 동기화 (SERVER= 옵션) |
| `deploy-test` | 전체 빌드 → push → deploy-test 배포 |
| `deploy-test-service` | 단일 서비스 배포 (SVC=frontend\|backend-api\|ai-pipeline) |

---

## 레거시 브랜치 (미사용)

아래 브랜치는 현재 사용하지 않음. 참고용으로만 유지.

| 브랜치 | 상태 | 비고 |
|--------|------|------|
| `main` | 미사용 | 프로젝트 초기 기준 |
| `develop` | 미사용 | 구 통합 브랜치 |
| `dev/*` (5개) | 미사용 | 구 팀원별 브랜치 → `dev-final/*`로 대체 |
| `release/feb20-stable` | 보존 | 091a1bb 기준선 (롤백용) |
| `prod` | 미사용 | 구 프로덕션 브랜치 → `prod-final`로 대체 |
