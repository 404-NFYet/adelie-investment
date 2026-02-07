# 기여 가이드

## 브랜치 전략

```
main          # 프로덕션 (보호됨, PR만 가능)
├── develop   # 통합 브랜치
│   ├── feature/차트-시스템     # 기능 개발
│   ├── feature/자유매매        # 기능 개발
│   ├── fix/네러티브-오류       # 버그 수정
│   └── hotfix/인증-보안      # 긴급 수정
```

- **feature/\***: develop에서 분기, develop으로 PR
- **fix/\***: develop에서 분기, develop으로 PR
- **hotfix/\***: main에서 분기, main과 develop 양쪽에 PR

## 커밋 컨벤션

```
feat: 차트 컴포넌트 시스템 추가
fix: 내러티브 스텝 인덱스 오류 수정
docs: SETUP.md 환경 변수 항목 추가
refactor: 포트폴리오 서비스 쿼리 최적화
test: 파이프라인 검증 테스트 추가
chore: Dockerfile 빌드 캐시 개선
style: ESLint 경고 해결
```

형식: `<type>: <한글 설명>`

## PR 프로세스

1. feature 브랜치에서 개발
2. `make dev`로 로컬 테스트 확인
3. `make test`로 테스트 통과 확인
4. PR 생성 (develop 대상)
5. 리뷰어 1명 이상 승인
6. CI 통과 후 Squash Merge

## PR 템플릿

```markdown
## 변경 사항
- 무엇을 왜 변경했는지 간단히 설명

## 테스트
- [ ] make test-backend 통과
- [ ] make test-e2e 통과 (해당되는 경우)
- [ ] 로컬에서 수동 테스트 완료

## 스크린샷 (UI 변경 시)
```

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
