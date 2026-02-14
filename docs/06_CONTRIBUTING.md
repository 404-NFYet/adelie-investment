# 기여 가이드

> 대상 독자: 전체 팀원
> 브랜치 전략, 커밋 컨벤션, PR 워크플로우, 모듈 소유권, 릴리스 프로세스를 다룹니다.

---

## 브랜치 전략

```
prod (프로덕션 배포 — 보호됨, PR만 가능)
 └── develop (통합 — 보호됨, 도형준 관리)
      ├── dev/frontend     # 손영진
      ├── dev/chatbot      # 정지훈
      ├── dev/pipeline     # 안례진
      ├── dev/backend      # 허진서
      └── dev/infra        # 도형준

main (소개 페이지 — 코드 없음, README + docs만)
```

### 브랜치 역할

| 브랜치 | 역할 | 보호 | 머지 방향 |
|--------|------|------|-----------|
| `prod` | 프로덕션 배포 (deploy-test) | force push 금지, PR 필수 | develop → prod |
| `develop` | 통합 브랜치 | force push 금지, PR 필수 | dev/* → develop |
| `dev/{part}` | 팀원별 개발 | - | 자유 push |
| `main` | 팀/서비스 소개 페이지 | - | 독립 (코드 없음) |
| `hotfix/*` | 긴급 수정 | - | prod에서 분기 → prod + develop |

### 일상 워크플로우

```bash
# 1. 내 브랜치에서 작업
git checkout dev/backend
git pull origin dev/backend

# 2. 작업 + 커밋
git add <files>
git commit -m "feat: 사용자 프로필 API 추가"

# 3. 푸시
git push origin dev/backend

# 4. PR 생성 (dev/backend → develop)
gh pr create --base develop --title "feat: 사용자 프로필 API 추가"
```

### feature 브랜치 (선택)

큰 작업은 dev/{part}에서 추가 브랜치를 만들 수 있습니다:

```bash
git checkout dev/backend
git checkout -b feat/backend/user-profile
# 작업 후 dev/backend에 로컬 머지 또는 PR
```

---

## 커밋 컨벤션

형식: `type: 한글 설명`

```
feat: 리더보드 API 추가
fix: 포트폴리오 크래시 수정
docs: 스케줄러 가이드 추가
refactor: 포트폴리오 서비스 쿼리 최적화
test: E2E 플로우 테스트 추가
chore: Dockerfile 빌드 캐시 개선
style: ESLint 경고 해결
perf: 리스트 컴포넌트 React.memo 적용
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
| `style` | 코드 포맷팅 (동작 변경 없음) |
| `perf` | 성능 개선 |

### 커밋 규칙

- AI 도구 흔적 금지: `Co-Authored-By`, `Generated with...` 등 포함하지 않음
- 커밋 전 `git config user.name`/`git config user.email`이 본인과 일치하는지 확인
- 논리적 단위로 분리: 한 커밋에 하나의 의미 있는 변경

---

## PR 워크플로우

### 1. dev/{part} → develop PR

```bash
# 브랜치 최신화
git checkout dev/backend
git pull origin develop  # develop 변경사항 반영
git push origin dev/backend

# PR 생성
gh pr create --base develop --title "feat: 사용자 프로필 API 추가"
```

- CODEOWNERS에 따라 자동 리뷰어 할당
- **최소 1명 승인** 필요
- 로컬 테스트 확인 (`make dev` + `make test`)
- **Squash Merge** 사용

### 2. develop → prod 릴리스 PR

```bash
# 릴리스 PR (도형준 또는 팀장)
gh pr create --base prod --head develop \
  --title "Release v0.9.1: 주요 변경 요약"
```

- 전체 팀원 확인
- 배포 후: `make deploy-test`

### PR 체크리스트

PR 생성 시 `.github/PULL_REQUEST_TEMPLATE.md` 템플릿이 자동 적용됩니다.
영향 받는 파트를 반드시 체크하여 관련 담당자가 리뷰할 수 있도록 합니다.

---

## 모듈별 소유권

| 모듈 | 담당자 | 역할 |
|------|--------|------|
| `frontend/` | @YJ99Son (손영진) | PM / Frontend |
| `fastapi/` | @jjjh02 (허진서) | Backend |
| `chatbot/` | @J2hoon10 (정지훈) | Chatbot |
| `datapipeline/` | @ryejinn (안례진) | Data Pipeline |
| `shared/` | @J2hoon10 @ryejinn | 공유 AI 설정 |
| `database/` | @jjjh02 @dorae222 | DB 마이그레이션 |
| `lxd/`, `.github/`, `Makefile` | @dorae222 (도형준) | Infra |
| `docs/` | @YJ99Son | 프로젝트 문서 |
| `tests/` | @ryejinn | 테스트 |

소유권은 `.github/CODEOWNERS` 파일로 관리되며, PR 생성 시 자동으로 리뷰어가 할당됩니다.

### 담당자 Git 정보

| 이름 | git user.name | git user.email |
|------|--------------|----------------|
| 손영진 | YJ99Son | syjin2008@naver.com |
| 정지훈 | J2hoon10 | myhome559755@naver.com |
| 안례진 | ryejinn | arj1018@ewhain.net |
| 허진서 | jjjh02 | jinnyshur0104@gmail.com |
| 도형준 | dorae222 | dhj9842@gmail.com |

---

## Docker 태깅 + Git 연동

| Git 이벤트 | Docker 태그 | 예시 |
|------------|------------|------|
| develop → prod 머지 | `latest` | `make build && make push` |
| prod 태그 (v*) | `v{M.m.p}` | `make build TAG=v0.9.1 && make push TAG=v0.9.1` |
| 개발 중 테스트 | `dev-{SHA}` | `make build TAG=dev-$(git rev-parse --short HEAD)` |

---

## 릴리스 프로세스

1. develop 브랜치 안정화 확인 (테스트 통과)
2. develop → prod PR 생성 (`Release vX.Y.Z: 주요 변경 요약`)
3. prod 머지 후 태그 생성

```bash
git checkout prod
git pull origin prod
git tag v0.9.1
git push origin v0.9.1
```

4. 프로덕션 배포

```bash
make build TAG=v0.9.1 && make push TAG=v0.9.1
make deploy-test
```

### 버전 규칙

- **Major (vX.0.0)**: 대규모 구조 변경, 비호환 변경
- **Minor (v0.X.0)**: 기능 추가, UI 개편 등
- **Patch (v0.0.X)**: 버그 수정, 핫픽스

---

## 코드 스타일

- **Frontend**: JavaScript, Tailwind CSS, 함수형 컴포넌트
- **FastAPI**: Python 3.11+, 비동기(async/await), 한글 주석
- **Chatbot / Pipeline**: Python, 한글 주석, 마크다운 프롬프트

## 파일 구조 규칙

- 새 컴포넌트: `frontend/src/components/{domain|common|layout}/`
- 새 API 라우트: `fastapi/app/api/routes/`
- 새 서비스: `fastapi/app/services/`
- 새 프롬프트 (튜터): `chatbot/prompts/templates/`
- 새 프롬프트 (파이프라인): `datapipeline/prompts/templates/`
- 새 테스트: `tests/` 또는 `frontend/e2e/`
