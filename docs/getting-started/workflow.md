# 개발 워크플로우 가이드

이 문서는 Adelie Investment 프로젝트의 일상 개발 사이클, 브랜치 전략, 커밋 규칙, PR 프로세스를 설명합니다.

## 1. 일상 개발 사이클

### 하루 시작
```bash
# 1. 원격 저장소에서 최신 변경사항 가져오기
git checkout develop
git pull origin develop

# 2. 작업 브랜치로 이동
git checkout dev/frontend  # 각자 담당 파트 브랜치

# 3. develop 최신 변경사항 반영
git merge develop

# 4. Docker 이미지 최신화 (다른 팀원이 업데이트한 경우)
docker compose -f docker-compose.dev.yml pull
docker compose -f docker-compose.dev.yml up -d

# 5. 개발 환경 시작
make dev
```

### 코드 수정 및 테스트
```bash
# 파일 수정 (에디터 사용)
# frontend/src/**, fastapi/app/**, chatbot/**, datapipeline/** 등

# 자동 반영 확인
# - 프론트엔드: 브라우저 자동 새로고침 (HMR)
# - 백엔드: uvicorn 자동 재시작

# 수동 테스트
# - 프론트엔드: http://localhost:3001
# - 백엔드 API: http://localhost:8082/docs

# 자동 테스트 실행
make test              # 백엔드 유닛 테스트
make test-e2e          # E2E 테스트
pytest tests/test_foo.py -v  # 특정 테스트만
```

### 커밋 및 푸시
```bash
# 1. git config 확인 (담당자와 일치하는지)
git config user.name   # 예: YJ99Son
git config user.email  # 예: syjin2008@naver.com

# 2. 변경사항 확인
git status
git diff

# 3. 스테이징 (파일별로 추가)
git add frontend/src/pages/HomePage.jsx
git add frontend/src/components/common/Button.jsx

# 4. 커밋 (논리적 단위로 분리)
git commit -m "feat: 홈페이지 키워드 카드 레이아웃 개선"
git commit -m "refactor: 공통 버튼 컴포넌트 스타일 통일"

# 5. 원격 저장소에 푸시
git push origin dev/frontend
```

### 하루 마무리
```bash
# 작업 중인 변경사항 커밋 (WIP 커밋도 괜찮음)
git add .
git commit -m "wip: 키워드 필터링 기능 진행 중"
git push origin dev/frontend

# 개발 환경 종료 (선택)
make dev-down
```

## 2. 브랜치 전략

### 브랜치 구조
```
main            # 프로덕션 배포 브랜치 (보호됨)
  ↑
develop         # 개발 통합 브랜치 (보호됨)
  ↑
dev/frontend    # 손영진 (React UI)
dev/chatbot     # 정지훈 (AI 개발)
dev/pipeline    # 안례진 (AI QA)
dev/backend     # 허진서 (백엔드)
dev/infra       # 도형준 (인프라)
```

### 브랜치 규칙
- **main**: 프로덕션 배포 전용, 직접 커밋 금지, force push 절대 금지
- **develop**: 개발 통합 브랜치, PR로만 머지, force push 금지
- **dev/\***: 각 팀원의 작업 브랜치, 자유롭게 커밋 가능

### 브랜치 생성
새로운 기능 개발 시:

```bash
# develop에서 분기
git checkout develop
git pull origin develop

# feature 브랜치 생성 (선택)
git checkout -b feature/keyword-filter

# 작업 후 dev/* 브랜치로 머지
git checkout dev/frontend
git merge feature/keyword-filter
git push origin dev/frontend

# feature 브랜치 삭제 (선택)
git branch -d feature/keyword-filter
```

### 브랜치 간 동기화
다른 팀원의 변경사항 반영:

```bash
# develop 최신화
git checkout develop
git pull origin develop

# 작업 브랜치에 반영
git checkout dev/frontend
git merge develop

# 충돌 해결 (발생 시)
# 에디터에서 충돌 파일 수정 후
git add .
git commit -m "chore: develop 머지 및 충돌 해결"
git push origin dev/frontend
```

## 3. 커밋 컨벤션

### 커밋 메시지 형식
```
type: 한글 설명

예시:
feat: 키워드 카드 즐겨찾기 기능 추가
fix: 로그인 토큰 만료 처리 버그 수정
refactor: 튜터 에이전트 프롬프트 구조 개선
chore: Docker 이미지 빌드 스크립트 업데이트
docs: API 문서에 인증 엔드포인트 설명 추가
test: 포트폴리오 API 통합 테스트 작성
style: 코드 포맷팅 (Prettier)
perf: 키워드 목록 조회 쿼리 최적화
```

### Type 분류
| Type | 용도 | 예시 |
|------|------|------|
| feat | 새로운 기능 추가 | `feat: 실시간 주가 차트 컴포넌트 구현` |
| fix | 버그 수정 | `fix: 튜터 응답 스트리밍 중단 문제 해결` |
| refactor | 코드 리팩토링 (기능 변경 없음) | `refactor: API 클라이언트 에러 핸들링 개선` |
| chore | 빌드/설정 변경 | `chore: Dockerfile Python 버전 3.11로 업그레이드` |
| docs | 문서 수정 | `docs: 데이터 파이프라인 실행 가이드 추가` |
| test | 테스트 추가/수정 | `test: 키워드 크롤러 유닛 테스트 작성` |
| style | 코드 스타일 변경 (포맷팅, 세미콜론 등) | `style: ESLint 규칙 적용` |
| perf | 성능 개선 | `perf: Redis 캐싱으로 API 응답 속도 개선` |

### 커밋 전 체크리스트
```bash
# 1. git config 확인
git config user.name   # 자신의 이름과 일치하는지
git config user.email  # 자신의 이메일과 일치하는지

# 일치하지 않으면 설정
git config user.name "YJ99Son"
git config user.email "syjin2008@naver.com"

# 2. 변경사항 리뷰
git status
git diff

# 3. 논리적 단위로 커밋 분리
# 나쁜 예: 모델 + 라우트 + 프론트 + 테스트 한 번에 커밋
# 좋은 예: 각각 별도 커밋
git add fastapi/app/models/notification.py
git commit -m "feat: 알림 모델 추가"

git add fastapi/app/api/routes/notification.py
git commit -m "feat: 알림 API 엔드포인트 구현"

git add frontend/src/api/notification.js
git commit -m "feat: 알림 API 클라이언트 연동"

git add tests/backend/test_notification.py
git commit -m "test: 알림 API 통합 테스트 추가"
```

### 금지 사항
- **Co-Authored-By 태그 절대 금지**: 커밋 메시지에 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` 같은 AI 도구 흔적 남기지 않음
- **AI 도구 언급 금지**: "Generated with Claude Code", "AI-assisted" 등 표기 금지
- **--no-verify 사용 금지**: pre-commit hook 우회 금지 (사용자 명시 요청 제외)
- **force push to main/develop 금지**: 협업 브랜치에 강제 푸시 절대 금지
- **거대 커밋 금지**: 100개 파일 이상 한 번에 커밋하지 않음 (논리적으로 분리)

## 4. PR (Pull Request) 규칙

### PR 생성
```bash
# 1. 작업 브랜치에서 최신 develop 반영
git checkout dev/frontend
git merge develop
git push origin dev/frontend

# 2. GitHub에서 PR 생성
# Base: develop ← Compare: dev/frontend

# 3. PR 제목 및 설명 작성
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

### PR 설명 템플릿
```markdown
## 변경사항
- 키워드 카드에 즐겨찾기 버튼 추가
- 즐겨찾기 상태 localStorage에 저장
- 즐겨찾기 키워드만 필터링하는 토글 추가

## 테스트
- [ ] 로컬 환경에서 기능 동작 확인
- [ ] 관련 유닛 테스트 작성/통과
- [ ] E2E 테스트 통과 (해당 시)

## 스크린샷
(UI 변경 시 스크린샷 첨부)

## 관련 이슈
Closes #123
```

### PR 리뷰 프로세스
1. **PR 생성자**: 코드 리뷰 요청 (Slack/Discord 알림)
2. **리뷰어**: 최소 1명 이상 Approve 필요
3. **리뷰어 체크리스트** (아래 섹션 참고)
4. **수정 요청 시**: 피드백 반영 후 재요청
5. **Approve 후**: PR 생성자 또는 팀장이 머지
6. **머지 후**: 원격 브랜치 삭제 (선택)

### PR 머지 전 체크
```bash
# develop 최신화 확인
git checkout develop
git pull origin develop

# 작업 브랜치에 반영
git checkout dev/frontend
git merge develop

# 충돌 해결 후 푸시
git push origin dev/frontend

# GitHub에서 "Merge pull request" 클릭
```

## 5. 다른 팀원의 변경 반영

### Docker 이미지 업데이트
다른 팀원이 Dockerfile 또는 의존성을 변경한 경우:

```bash
# 최신 이미지 pull
docker compose -f docker-compose.dev.yml pull

# 컨테이너 재시작
docker compose -f docker-compose.dev.yml up -d

# 로그 확인 (문제 발생 시)
docker compose -f docker-compose.dev.yml logs -f backend-api
```

### 코드 변경 반영
develop 브랜치에 새로운 커밋이 머지된 경우:

```bash
# develop 최신화
git checkout develop
git pull origin develop

# 작업 브랜치에 반영
git checkout dev/frontend
git merge develop

# 충돌 해결 (발생 시)
# 에디터에서 충돌 파일 수정 후
git add .
git commit -m "chore: develop 머지 및 충돌 해결"

# 푸시
git push origin dev/frontend
```

### DB 스키마 변경 반영
다른 팀원이 Alembic 마이그레이션을 추가한 경우:

```bash
# 최신 코드 pull
git pull origin develop

# 마이그레이션 실행
make migrate

# 또는 직접 실행
docker compose --profile migrate run db-migrate

# 적용 확인
docker compose --profile migrate run db-migrate alembic current
```

### 환경변수 변경 반영
`.env` 파일이 업데이트된 경우:

```bash
# .env 파일 확인
git pull origin develop
cat .env

# 새로운 환경변수 추가 확인
# 필요 시 로컬 .env에 값 설정

# 컨테이너 재시작 (환경변수 반영)
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up -d
```

## 6. 코드 리뷰 체크리스트

### 기능 검증
- [ ] 요구사항이 제대로 구현되었는가?
- [ ] 엣지 케이스가 처리되었는가? (빈 값, null, 에러 상황)
- [ ] 기존 기능에 영향을 주지 않는가? (regression)

### 코드 품질
- [ ] 코드가 명확하고 이해하기 쉬운가?
- [ ] 한글 주석이 적절히 작성되었는가?
- [ ] 중복 코드가 없는가? (DRY 원칙)
- [ ] 함수/컴포넌트가 단일 책임 원칙을 따르는가?

### 성능 및 보안
- [ ] API 키가 하드코딩되지 않았는가? (환경변수 사용)
- [ ] 민감 정보가 로그에 출력되지 않는가?
- [ ] N+1 쿼리 문제가 없는가? (DB 조회 최적화)
- [ ] 불필요한 API 호출이 없는가?

### 테스트
- [ ] 유닛 테스트가 작성되었는가? (핵심 로직)
- [ ] 테스트가 통과하는가? (`make test`)
- [ ] E2E 테스트가 필요한 경우 작성되었는가?

### 문서화
- [ ] API 변경 시 Swagger 문서가 업데이트되었는가?
- [ ] 복잡한 로직에 주석이 있는가?
- [ ] README 또는 가이드 문서 업데이트가 필요한가?

### 컨벤션 준수
- [ ] 커밋 메시지가 컨벤션을 따르는가? (`type: 한글 설명`)
- [ ] 파일/폴더 구조가 프로젝트 규칙을 따르는가?
- [ ] 코드 스타일이 일관적인가? (Prettier/ESLint/Black)

### Backend 특화
- [ ] Pydantic 스키마가 정의되었는가?
- [ ] SQLAlchemy 모델이 올바른가? (관계 설정, 인덱스)
- [ ] FastAPI 의존성 주입이 적절한가? (`get_current_user` 등)
- [ ] 비동기 함수가 올바르게 사용되었는가? (`async`/`await`)

### Frontend 특화
- [ ] 컴포넌트가 재사용 가능한 구조인가?
- [ ] Context API 사용이 적절한가? (불필요한 전역 상태 금지)
- [ ] API 클라이언트가 도메인별로 분리되어 있는가?
- [ ] 모바일 반응형이 적용되었는가? (max-width: 480px)
- [ ] Tailwind CSS 클래스가 일관적으로 사용되었는가?

## 7. 긴급 핫픽스 워크플로우

프로덕션에 치명적 버그 발생 시:

```bash
# 1. main에서 hotfix 브랜치 생성
git checkout main
git pull origin main
git checkout -b hotfix/fix-critical-bug

# 2. 버그 수정 및 테스트
# 코드 수정...
make test

# 3. 커밋
git add .
git commit -m "fix: 로그인 실패 시 서버 크래시 버그 수정"

# 4. main으로 PR 생성 (긴급)
git push origin hotfix/fix-critical-bug

# 5. 리뷰 및 머지 (최소한의 리뷰)
# GitHub PR: Base: main ← Compare: hotfix/fix-critical-bug

# 6. 머지 후 develop에도 반영
git checkout develop
git merge main
git push origin develop

# 7. 배포
make deploy
```

## 참고 자료
- [Git 브랜치 전략](https://nvie.com/posts/a-successful-git-branching-model/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [프로젝트 CLAUDE.md](/CLAUDE.md) - Git 규칙 상세
- [Docker 사용 가이드](/docs/02_도커.md)
