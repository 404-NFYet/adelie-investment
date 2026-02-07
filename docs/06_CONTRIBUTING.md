# 기여 가이드

> 대상 독자: 전체 팀원
> Git 브랜치 전략, 커밋 컨벤션, PR 워크플로우, 릴리스 프로세스, 모노레포 구조를 다룹니다.

---

## 브랜치 전략

간소화된 Git Flow를 사용합니다.

```
main (production — 보호됨, PR만 가능)
 └── develop (integration)
      ├── feat/<담당자>/<설명>    # 기능 개발
      ├── fix/<담당자>/<설명>     # 버그 수정
      ├── docs/<설명>             # 문서 작업
      ├── chore/<설명>            # 인프라/빌드
      └── hotfix/<설명>           # 긴급 수정 (main에서 분기)
```

### 브랜치 유형

| 접두사 | 분기 원점 | 머지 대상 | 용도 |
|--------|----------|----------|------|
| `feat/` | develop | develop | 기능 개발 |
| `fix/` | develop | develop | 버그 수정 |
| `docs/` | develop | develop | 문서 작업 |
| `chore/` | develop | develop | 인프라, 빌드, CI |
| `hotfix/` | main | main + develop | 프로덕션 긴급 수정 |

### 브랜치 네이밍 규칙

담당자 이니셜을 포함하여 누구의 작업인지 명확하게 합니다.

```
feat/hj/leaderboard-ui        # 기능: hj가 리더보드 UI 개발
fix/jh/portfolio-crash         # 수정: jh가 포트폴리오 크래시 수정
docs/scheduler-guide           # 문서: 담당자 생략 가능
chore/ci-workflow              # 인프라: 담당자 생략 가능
hotfix/auth-token-expire       # 긴급: main에서 분기
```

---

## 커밋 컨벤션

형식: `[type] 한글 설명`

```
[feat] 리더보드 API 추가
[fix] 포트폴리오 크래시 수정
[docs] 스케줄러 가이드 추가
[refactor] 포트폴리오 서비스 쿼리 최적화
[test] E2E 플로우 테스트 추가
[chore] Dockerfile 빌드 캐시 개선
[style] ESLint 경고 해결
```

### 커밋 타입

| 타입 | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 변경 |
| `refactor` | 기능 변경 없이 코드 구조 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, CI, 패키지 등 운영 작업 |
| `style` | 코드 포맷팅, 세미콜론 등 (동작 변경 없음) |

---

## PR 워크플로우

### 1. 브랜치 생성

```bash
git checkout develop
git pull origin develop
git checkout -b feat/hj/leaderboard-ui
```

### 2. 작업 + 커밋

```bash
# 작업 후
git add -A
git commit -m "[feat] 리더보드 API 추가"
```

### 3. PR 생성

```bash
git push -u origin feat/hj/leaderboard-ui
gh pr create --base develop --title "[feat] 리더보드 API 추가" --body "..."
```

### 4. 리뷰 + 머지

- CODEOWNERS에 따라 자동 리뷰어 할당
- **최소 1명 승인** 필요
- 로컬 테스트 확인 (`make dev` + `make test`)
- **Squash Merge** 사용 → feature 브랜치 자동 삭제

### PR 템플릿

```markdown
## 변경 사항
- 무엇을 왜 변경했는지 간단히 설명

## 테스트
- [ ] make test 통과
- [ ] make test-e2e 통과 (해당되는 경우)
- [ ] 로컬에서 수동 테스트 완료

## 스크린샷 (UI 변경 시)
```

---

## 릴리스 프로세스

1. develop 브랜치 안정화 확인 (테스트 통과, 주요 버그 없음)
2. develop → main PR 생성
   - 제목: `Release vX.Y.Z: 주요 변경 요약`
3. main 머지 후 태그 생성

```bash
git checkout main
git pull origin main
git tag v0.9.0
git push origin v0.9.0
```

4. 프로덕션 배포

```bash
make deploy
```

### 버전 규칙

- **Major (vX.0.0)**: 대규모 구조 변경, 비호환 변경
- **Minor (v0.X.0)**: 기능 추가, UI 개편 등
- **Patch (v0.0.X)**: 버그 수정, 핫픽스

---

## 모노레포 구조

```
adelie-investment/
├── frontend/                   # React 19 + Vite
├── backend_api/                # FastAPI
├── backend-spring/             # Spring Boot
├── ai_module/                  # LangGraph 튜터
├── data_pipeline/              # pykrx 데이터 수집
├── infra/                      # Docker Compose, Terraform
├── tests/                      # 통합 테스트
├── scripts/                    # 유틸리티 스크립트
├── docs/                       # 프로젝트 문서
├── .github/                    # GitHub 설정
├── Makefile                    # 빌드/배포 자동화
├── docker-compose.*.yml        # 환경별 Compose
└── CLAUDE.md                   # AI 개발 도구 설정
```

### 모듈별 소유권

| 모듈 | 담당자 | 설명 |
|------|--------|------|
| `frontend/` | @YJ99Son | React 프론트엔드 |
| `backend_api/` | @J2hoon10 | FastAPI 백엔드 |
| `backend-spring/` | @jjjh02 | Spring Boot 인증/CRUD |
| `ai_module/` | @J2hoon10 @ryejinn | LangGraph AI 튜터 |
| `data_pipeline/` | @J2hoon10 | 데이터 수집 파이프라인 |
| `infra/` | @dorae222 | Docker, Terraform, CI/CD |
| `docs/` | @YJ99Son | 프로젝트 문서 |
| `tests/` | @ryejinn | 통합 테스트, QA |

소유권은 `.github/CODEOWNERS` 파일로 관리되며, PR 생성 시 자동으로 리뷰어가 할당됩니다.

---

## 코드 스타일

- **Frontend**: JavaScript, Tailwind CSS, 함수형 컴포넌트
- **FastAPI**: Python 3.11+, 비동기(async/await), 한글 주석
- **Spring Boot**: Java 17, 어노테이션 기반
- **AI Module**: Python, 한글 주석, 마크다운 프롬프트

## 파일 구조 규칙

- 새 컴포넌트: `frontend/src/components/{domain|common|layout}/`
- 새 API 라우트: `backend_api/app/api/routes/`
- 새 서비스: `backend_api/app/services/`
- 새 프롬프트: `ai_module/prompts/templates/`
- 새 테스트: `tests/` 또는 `frontend/e2e/`
