# Adelie Investment — 빠른 시작 가이드

> 처음 합류하거나 환경을 새로 세팅할 때 이 문서를 따라하세요.

---

## 1. 내 개발 서버 접속

`~/.ssh/config`에 아래 내용을 추가한 뒤:

```
Host dev-yj99son
    HostName 10.10.10.14
    User ubuntu

Host dev-j2hoon10
    HostName 10.10.10.11
    User ubuntu

Host dev-jjjh02
    HostName 10.10.10.12
    User ubuntu

Host dev-ryejinn
    HostName 10.10.10.13
    User ubuntu

Host dev-hj
    HostName 10.10.10.15
    User ubuntu
```

```bash
ssh dev-<내이름>     # 예: ssh dev-jjjh02
```

---

## 2. 최신 코드 받기

```bash
cd ~/adelie-investment
git pull origin dev-final/<내역할>    # 예: dev-final/backend
```

---

## 3. 개발 서버 실행

```bash
make dev        # 전체 스택 (frontend + backend-api + postgres + redis)
make migrate    # DB 마이그레이션 (처음 세팅 또는 migration 파일 추가 시)
```

---

## 매일 쓰는 명령어

| 상황 | 명령어 |
|------|--------|
| 서버 실행 | `make dev` |
| 서버 중지 | `make dev-down` |
| 상태 확인 | `make status` |
| 테스트 실행 | `make test` |
| DB 마이그레이션 | `make migrate` |
| 로그 보기 | `make logs` |
| Docker 캐시 정리 | `make clean` |

---

## 브랜치 워크플로우 (요약)

```
main            ← 소개/README용 (CI/CD 없음)
  └── develop   ← 배포 브랜치 (develop push → deploy-test 자동 배포)
        └── dev-final/<역할>  ← 개인 개발 서버 자동 배포
              └── feature/*   ← 개인 피처 작업
```

### 일반 작업 흐름

```bash
# 1. 피처 작업
git checkout -b feature/내기능
# ... 작업 ...
git add <파일>
git commit -m "feat: 기능 설명"
git push origin feature/내기능

# 2. PR 생성 → dev-final/<내역할> 타겟
gh pr create --base dev-final/<내역할> --title "feat: 기능 설명"

# 3. PR 머지 후 dev-final이 develop으로 PR
gh pr create --base develop --head dev-final/<내역할> --title "chore: <역할> → develop 동기화"

# 4. develop merge → deploy-test 자동 배포
```

### 역할별 브랜치 정보

| 팀원 | LXD 서버 | 개발 브랜치 |
|------|---------|------------|
| 손영진 (팀장) | dev-yj99son | dev-final/frontend |
| 정지훈 (AI) | dev-j2hoon10 | dev-final/chatbot |
| 허진서 (백엔드) | dev-jjjh02 | dev-final/backend |
| 안례진 (QA) | dev-ryejinn | dev-final/pipeline |
| 도형준 (인프라) | dev-hj | dev-final/infra |

---

## GitHub 인증 설정 (PAT)

```bash
# 내 LXD 서버에서 1회 실행
cd ~/adelie-investment
git remote set-url origin https://<ghp_YOUR_TOKEN>@github.com/404-NFYet/adelie-investment.git

# 확인
git ls-remote origin HEAD
```

---

## 상세 문서

- [Git 워크플로우](docs/reference/git-workflow.md)
- [Make 명령어 전체](docs/reference/make-commands.md)
- [프로젝트 아키텍처](CLAUDE.md)
