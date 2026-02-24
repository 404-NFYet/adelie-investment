# 팀 Git 워크플로우 가이드

> 최종 업데이트: 2026-02-24

---

## 브랜치 전략

```
main                    ← 소개/README용 (CI/CD 없음)
  └── develop           ← 배포 브랜치 (push → deploy-test 자동 배포)
        └── dev-final/* ← 팀원별 개발 서버 자동 배포
              └── feature/* ← 개인 피처 작업 (CI 실행)
```

| 브랜치 | 용도 | CI | 배포 |
|--------|------|----|------|
| `main` | 소개/README용 | ❌ | ❌ |
| `develop` | 통합 개발 브랜치 | ✅ PR 필수 | ✅ deploy-test (:latest) |
| `dev-final/*` | 팀원별 개발 서버 | ✅ (non-blocking) | ✅ 해당 LXD 서버 |
| `feature/*` | 개인 피처 작업 | ✅ | ❌ |
| `hotfix/*` | 긴급 버그 수정 | ✅ | ❌ |

### PR 규칙

| 대상 브랜치 | merge 방법 | 리뷰 |
|------------|-----------|------|
| `develop` | PR from dev-final/* | CI 통과 필수 |
| `dev-final/*` | 직접 push 또는 PR from feature/* | 불필요 |

---

## 담당자별 작업 브랜치

| 팀원 | git user.name | LXD 서버 | 개발 브랜치 |
|------|--------------|----------|------------|
| 손영진 (팀장) | YJ99Son | dev-yj99son | dev-final/frontend |
| 정지훈 (AI) | J2hoon10 | dev-j2hoon10 | dev-final/chatbot |
| 허진서 (백엔드) | jjjh02 | dev-jjjh02 | dev-final/backend |
| 안례진 (QA) | ryejinn | dev-ryejinn | dev-final/pipeline |
| 도형준 (인프라) | dorae222 | dev-hj | dev-final/infra |

---

## 일상 작업 흐름

### 1. 작업 시작 (개인 LXD 서버에서)

```bash
cd ~/adelie-investment

# 최신 코드 받기
git pull origin dev-final/<내_역할>

# 새 피처 브랜치 생성 (선택)
git checkout -b feature/my-feature
```

### 2. 코드 작성 후 커밋

```bash
# 변경 파일 확인
git status
git diff

# 스테이징 (특정 파일 지정 — git add . 지양)
git add src/components/MyComponent.jsx
git add fastapi/app/api/routes/my_route.py

# 커밋
git commit -m "feat: 기능 설명 (한글)"
```

### 3. Push

```bash
# 피처 브랜치 push
git push origin feature/my-feature

# 또는 dev-final/* 직접 push (소규모 수정)
git push origin dev-final/<내_역할>
# → 자동으로 해당 LXD 서버에 배포됨 (GitHub Actions)
```

### 4. PR 생성

```bash
# feature/* → dev-final/<내역할>
gh pr create \
  --base dev-final/<내_역할> \
  --title "feat: 기능 요약" \
  --body "변경 내용 설명"
```

### 5. develop 반영

```bash
# dev-final/* → develop PR 생성 (팀장 또는 역할 담당자가 리뷰)
gh pr create \
  --base develop \
  --head dev-final/<내_역할> \
  --title "chore: dev-final/<역할> → develop 동기화"

# develop push 후 deploy-test 자동 배포 (GitHub Actions)
```

---

## GitHub Actions CI/CD

| 워크플로우 | 트리거 | 동작 |
|-----------|--------|------|
| `ci.yml` | PR to develop/main/dev-final/* | lint + test (non-blocking for dev-final) |
| `deploy-develop.yml` | push to develop | 빌드 → Docker Hub :latest → deploy-test 배포 |
| `deploy-lxd.yml` | push to dev-final/* | 해당 LXD 서버 git pull + compose up |
| `main.yml` | push (전체) | Discord 알림 |
| `claude.yml` | @claude 멘션 | Claude 응답 |
| `claude-code-review.yml` | PR | 자동 코드 리뷰 |

### deploy-lxd.yml 사전 조건 (일회성)

deploy-test의 SSH 키를 각 LXD 서버에 등록해야 합니다:

```bash
# deploy-test에서 실행
ssh-keygen -t ed25519 -f ~/.ssh/lxd_deploy -N ""
for ip in 10.10.10.14 10.10.10.11 10.10.10.12 10.10.10.13 10.10.10.15; do
  ssh-copy-id -i ~/.ssh/lxd_deploy.pub ubuntu@$ip
done
```

---

## 커밋 컨벤션

### 형식

```
<type>: <한글 설명>
```

### 타입

| 타입 | 설명 |
|------|------|
| `feat` | 새 기능 추가 |
| `fix` | 버그 수정 |
| `refactor` | 코드 리팩토링 (기능 변경 없음) |
| `chore` | 빌드/설정/의존성 변경 |
| `docs` | 문서 수정 |
| `test` | 테스트 추가/수정 |
| `style` | 코드 스타일 변경 (포매팅 등) |
| `perf` | 성능 개선 |

### 예시

```bash
feat: 키워드 카드 즐겨찾기 기능 추가
fix: 튜터 SSE 스트리밍 연결 끊김 버그 수정
chore: alembic migration 파일 develop 기준 동기화
docs: git 워크플로우 가이드 추가
```

### 금지 사항

```bash
# ❌ Co-Authored-By 절대 금지
git commit -m "feat: 기능" --trailer "Co-Authored-By: Claude <noreply@anthropic.com>"

# ❌ AI 생성 흔적 금지 (커밋 메시지, PR 본문 모두)
"Generated with Claude Code"

# ❌ --no-verify 금지 (사용자 명시 요청 제외)
git commit --no-verify

# ❌ main/develop force push 절대 금지
git push --force origin main
```

---

## PAT 설정 방법 (HTTPS 토큰 방식) {#pat-설정-방법-https-토큰-방식}

각 LXD 서버에서 1회 실행. **PAT 값은 본인만 알고 있어야 함.**

```bash
# LXD 서버 접속
lxc exec dev-<이름> -- bash

# GitHub PAT가 포함된 remote URL 설정
cd /home/ubuntu/adelie-investment
git remote set-url origin https://<ghp_YOUR_TOKEN>@github.com/404-NFYet/adelie-investment.git

# 설정 확인 (마스킹됨)
git remote get-url origin | sed 's|https://[^@]*@|https://***@|g'
# → https://***@github.com/404-NFYet/adelie-investment.git

# 연결 테스트
git ls-remote origin HEAD
```

> PAT 만료 시: GitHub → Settings → Developer Settings → Personal Access Tokens → Regenerate

---

## 동기화 명령어

### 코드 동기화

```bash
# 내 서버 코드 최신화 (각 서버에서 직접)
cd ~/adelie-investment
git pull origin dev-final/<내_역할>

# 인프라에서 전체 서버 일괄 동기화
make -f lxd/Makefile sync
```

### DB 동기화

```bash
# prod 데이터를 개인 로컬 DB에 복제 (최초 세팅 또는 데이터 초기화 시)
make -f lxd/Makefile db-local-setup

# prod 데이터만 재동기화 (alembic은 건드리지 않음)
make -f lxd/Makefile db-sync
```

### migration 추가 시 주의사항

1. **#migration 채널에 먼저 공지** (충돌 방지)
2. 한 번에 1명만 migration 파일 작성
3. 작성 완료 → develop에 push → 다음 사람에게 알림
4. 각 LXD 서버에서 `git pull` 후 `alembic upgrade heads` 실행

---

## 서버 상태 확인

```bash
# 전체 서버 헬스체크 (브랜치 + 컨테이너 상태)
make -f lxd/Makefile health

# git 설정 점검 (user, email, remote URL)
make -f lxd/Makefile git-check

# JWT_SECRET 기본값 서버 자동 갱신
make -f lxd/Makefile jwt-fix
```

---

## Alembic 현재 상태 기준 (2026-02-24)

| 환경 | Alembic Head | 비고 |
|------|-------------|------|
| deploy-test (prod) | `20260223_expires` | 기준 버전 |
| dev-yj99son | `20260223_expires`, `c1d4e8f92b3a` | flashcards 추가 head |
| dev-j2hoon10 | `20260223_expires` | ✅ |
| dev-jjjh02 | `20260223_expires` | ✅ |
| dev-ryejinn | `20260223_expires` | ✅ |
| dev-hj | `20260223_expires` | ✅ |

> `alembic upgrade heads` (복수형) 사용 권장 — multiple head 환경에서 안전
