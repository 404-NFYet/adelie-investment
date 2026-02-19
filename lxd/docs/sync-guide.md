# 브랜치 싱크 가이드

develop → dev/* 브랜치 싱크 및 LXD 서버 업데이트 워크플로우

---

## 브랜치 계층 구조

```
main
 └── develop                ← 통합 브랜치 (항상 배포 가능 상태 유지)
      ├── dev/frontend      ← 손영진 (YJ99Son) — React UI
      ├── dev/backend       ← 허진서 (jjjh02) — FastAPI 인증/DB
      ├── dev/chatbot       ← 정지훈 (J2hoon10) — AI 튜터/LangGraph
      ├── dev/pipeline      ← 안례진 (ryejinn) — 데이터 파이프라인
      └── dev/infra         ← 도형준 (dorae222) — Docker/CI/CD
```

### 담당자별 브랜치 매핑

| 담당자 | git user.name | 브랜치 | LXD 컨테이너 |
|--------|-------------|--------|-------------|
| 손영진 | YJ99Son | dev/frontend | dev-yj99son |
| 허진서 | jjjh02 | dev/backend | dev-jjjh02 |
| 정지훈 | J2hoon10 | dev/chatbot | dev-j2hoon10 |
| 안례진 | ryejinn | dev/pipeline | dev-ryejinn |
| 도형준 | dorae222 | dev/infra | dev-hj |

---

## 개인 작업 흐름

### 1. 작업 시작 전 — develop 최신화

```bash
# 내 dev/* 브랜치에서 develop 최신 내용 가져오기
git fetch origin
git checkout dev/<파트명>
git merge origin/develop --no-edit
```

### 2. 기능 개발 — 서브브랜치 사용 권장

```bash
# dev/<파트> 에서 서브브랜치 생성
git checkout -b fix/ui-button dev/frontend

# 작업 후 dev/<파트>로 병합
git checkout dev/frontend
git merge fix/ui-button --no-edit
git branch -d fix/ui-button
git push origin dev/frontend
```

### 3. dev/* → develop 반영 (PR)

기능 완성 후 GitHub에서 `dev/<파트>` → `develop` PR 생성.
- PR 제목: `feat: 기능 설명` (한글)
- 팀원 리뷰 후 merge (squash 금지, merge commit 사용)

---

## develop → dev/* 싱크

develop에 다른 팀원 작업이 반영됐을 때, 내 dev/* 브랜치를 최신화합니다.

### 방법 1: Makefile (인프라 담당자 — 일괄 싱크)

```bash
# develop → dev/* 5개 브랜치 자동 병합 & push (인프라 전용 Makefile)
make -f lxd/Makefile sync-dev-branches
```

> 실행 전 git config user.name / user.email이 dorae222 계정인지 확인하세요.
> 개인 싱크는 아래 방법 2를 사용하세요.

### 방법 2: 개별 싱크 (각 담당자)

```bash
git fetch origin
git checkout dev/<내 파트>
git merge origin/develop --no-edit
git push origin dev/<내 파트>
```

### 싱크 빈도

- **최소**: 작업 시작 전 (매일)
- **권장**: develop에 PR merge 될 때마다

---

## LXD 서버 코드 업데이트

### 방법 1: Makefile (일괄 업데이트)

```bash
# 모든 LXD 서버에서 git pull 실행 (인프라 전용 Makefile)
make -f lxd/Makefile sync-lxd

# 브랜치 싱크 + LXD 서버 동시 실행
make -f lxd/Makefile sync-all
```

### 방법 2: 개별 서버 직접 접속

```bash
# 내 서버에 접속하여 pull
lxc exec dev-<컨테이너명> -- bash

# 컨테이너 내부에서
cd /home/ubuntu/adelie-investment
git pull origin dev/<내 파트>
```

### 방법 3: 원격 명령 (lxc exec)

```bash
lxc exec dev-yj99son  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/frontend"
lxc exec dev-j2hoon10 -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/chatbot"
lxc exec dev-ryejinn  -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/pipeline"
lxc exec dev-jjjh02   -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/backend"
lxc exec dev-hj       -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/infra"
```

---

## 충돌 해결

### develop merge 중 충돌 발생 시

```bash
git merge origin/develop
# CONFLICT 발생 시:

# 1. 충돌 파일 확인
git status

# 2. 충돌 해결 (편집기로 <<<< ==== >>>> 마커 제거)
vi <충돌 파일>

# 3. 해결 후 스테이징
git add <충돌 파일>

# 4. 병합 완료
git merge --continue

# 5. push
git push origin dev/<파트>
```

### 충돌 포기 (이전 상태로 되돌리기)

```bash
git merge --abort
```

---

## deploy-test 서버 배포

deploy-test(10.10.10.20)는 develop 브랜치 기반 테스트 환경입니다.

```bash
# 전체 재배포
make -f lxd/Makefile deploy-test

# 특정 서비스만 재배포 (예: frontend)
make -f lxd/Makefile deploy-test-service SVC=frontend
```

> `deploy-test`는 내부적으로 `git pull origin develop`을 실행합니다.

---

## Quick Reference

```bash
# 작업 시작 전 (내 브랜치 최신화)
git fetch origin && git merge origin/develop --no-edit

# develop → 전체 dev/* 브랜치 싱크 (인프라 담당자)
make -f lxd/Makefile sync-dev-branches

# LXD 서버 전체 코드 업데이트
make -f lxd/Makefile sync-lxd

# 브랜치 + 서버 동시 싱크
make -f lxd/Makefile sync-all

# 내 LXD 서버에서 직접 pull
lxc exec dev-<컨테이너> -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/<파트>"

# 브랜치 현황 확인
git log --oneline develop..origin/dev/frontend   # develop보다 앞선 커밋
git log --oneline origin/dev/frontend..develop   # develop보다 뒤처진 커밋

# deploy-test 배포
make -f lxd/Makefile deploy-test
```

---

## 검증 명령어

```bash
# dev/* 브랜치가 develop과 싱크됐는지 확인 (빈 결과 = 동기화 완료)
git log --oneline develop..origin/dev/frontend

# LXD 서버의 최신 커밋 확인
lxc exec dev-yj99son -- bash -c "cd ~/adelie-investment && git log --oneline -3"

# deploy-test 최신 커밋 확인
ssh deploy-test 'cd ~/adelie-investment && git log --oneline -3'
```
