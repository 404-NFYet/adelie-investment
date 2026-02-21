# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 모의투자 404 수정 + 문의사항 저장/대시보드 표시

## Context

**3개의 독립적인 버그:**

1. **모의투자 페이지 404** (최우선): 브라우저 콘솔에서 `GET /api/v1/portfolio 404 Not Found` 확인.
   - 원인: `pykrx` 패키지가 `fastapi/requirements.txt`에 누락 → 컨테이너에 미설치
   - → `stock_price_service.py`가 `from pykrx import stock`으로 top-level import
   - → `portfolio.py`가 `stock_price_service`...

### Prompt 2

배포서버까지 업데이트가 진행되었는가? 아니라면 진행해라

### Prompt 3

frontend도 진행했나?

### Prompt 4

아직 문의사항이 올바르게 작동하지 않는 것 같다.

