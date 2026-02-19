---
name: sync
description: sync-guide 기준으로 dev/frontend를 develop과 싱크하고 상태 확인
user_invocable: true
---

# Sync Skill

`/home/ubuntu/adelie-investment/lxd/docs/sync-guide.md`를 기준으로  
dev/frontend 브랜치를 develop 최신 상태로 동기화합니다.

## 사용법

`/sync $ARGUMENTS`

- `/sync` (인자 없음) — develop 최신 내용을 dev/frontend에 병합
- `/sync check` — 싱크 상태만 확인 (병합하지 않음)
- `/sync lxd` — LXD 서버(dev-yj99son)에 코드 업데이트
- `/sync full` — 브랜치 싱크 + LXD 서버 업데이트 + 상태 확인

## 실행 절차

### 기본 싱크 (`/sync`)

```bash
# 기준 문서 확인
sed -n '1,220p' /home/ubuntu/adelie-investment/lxd/docs/sync-guide.md

# 1. git config 확인
git config user.name   # YJ99Son 이어야 함
git config user.email  # syjin2008@naver.com 이어야 함

# 2. 현재 브랜치 확인
git branch --show-current  # dev/frontend 이어야 함

# 3. develop 최신화 병합
git fetch origin
git checkout dev/frontend
git merge origin/develop --no-edit

# 4. 충돌 발생 시 → 사용자에게 알리고 해결 지원
# 충돌 없으면 push
git push origin dev/frontend

# 5. 결과 확인
git log --oneline -5
```

### 상태 확인 (`/sync check`)

```bash
# develop보다 앞선 커밋
echo "=== develop보다 앞선 dev/frontend 커밋 ==="
git fetch origin
git log --oneline develop..origin/dev/frontend

# develop보다 뒤처진 커밋 (이게 있으면 싱크 필요)
echo "=== develop에는 있고 dev/frontend에는 없는 커밋 ==="
git log --oneline origin/dev/frontend..develop
```

### LXD 서버 업데이트 (`/sync lxd`)

```bash
lxc exec dev-yj99son -- bash -c "cd /home/ubuntu/adelie-investment && git pull origin dev/frontend"
```

### 전체 싱크 (`/sync full`)

1. 기본 싱크 실행
2. LXD 서버 업데이트 실행
3. 최종 상태 확인

## 충돌 해결 가이드

충돌 발생 시:
1. `git status`로 충돌 파일 목록 표시
2. 각 충돌 파일의 내용을 사용자에게 보여줌
3. 사용자가 선택할 수 있도록 옵션 제시:
   - 직접 해결 (편집)
   - 내 변경사항 우선 (`git checkout --ours`)
   - develop 변경사항 우선 (`git checkout --theirs`)
   - 병합 취소 (`git merge --abort`)

## 주의사항

- git config가 YJ99Son / syjin2008@naver.com 이 아니면 경고 후 중단
- dev/frontend 브랜치가 아니면 경고 후 중단
- 커밋되지 않은 변경사항이 있으면 경고 (stash 제안)
- 충돌 시 자동 해결하지 말고 사용자 선택을 우선
