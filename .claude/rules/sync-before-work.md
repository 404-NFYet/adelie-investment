---
paths: []
---

# 작업 전 브랜치 싱크 규칙

## 기준 문서 (Source of Truth)

- 항상 `/home/ubuntu/adelie-investment/lxd/docs/sync-guide.md`를 먼저 확인하고 절차를 따른다.
- 이 규칙 문서는 요약본이며, 충돌 시 `sync-guide.md` 내용을 우선한다.

## 담당자 정보

- 담당자: 손영진 (프론트엔드)
- git user.name: YJ99Son
- git user.email: syjin2008@naver.com
- 브랜치: dev/frontend
- LXD 컨테이너: dev-yj99son

## 작업 시작 전 필수 절차

코드 수정, 커밋, 또는 기능 개발을 시작하기 전에 반드시 다음을 확인하고 실행:

1. **git config 확인**: `git config user.name`이 `YJ99Son`, `git config user.email`이 `syjin2008@naver.com`인지 확인
2. **현재 브랜치 확인**: `dev/frontend` 브랜치인지 확인
3. **develop 싱크**:
   ```bash
   git fetch origin
   git checkout dev/frontend
   git merge origin/develop --no-edit
   ```
4. **충돌 발생 시**: 사용자에게 충돌 파일 목록을 보여주고 해결 방안 제시

## 싱크 확인 방법

```bash
# develop보다 앞선 커밋
git log --oneline develop..origin/dev/frontend

# develop보다 뒤처진 커밋 (빈 결과 = 동기화 완료)
git log --oneline origin/dev/frontend..develop
```

## 커밋 규칙

- 커밋 메시지: `type: 한글 설명` (예: `feat: 키워드 카드 즐겨찾기 기능 추가`)
- Co-Authored-By 절대 포함하지 않음
- AI 도구 사용 흔적 남기지 않음
- 커밋 후 push까지 한 세트로 수행
