# Phase 2: 확인 기반 라우팅

## 문제

에이전트가 사용자의 요청을 받으면 즉시 실행하여, 위험한 작업(매수/매도)도 확인 없이 진행되는 문제가 있었습니다.

## 해결

### 1. 액션 리스크 분류
```python
HIGH_RISK_ACTIONS = ["buy_stock", "sell_stock", "conditional_buy", "conditional_sell"]
MEDIUM_RISK_ACTIONS = ["cancel_order", "modify_order"]
```

### 2. 라우팅 응답 확장 (`TutorRouteResponse`)
```python
class TutorRouteResponse(BaseModel):
    decision: Literal["general", "canvas", "search", "confirm_action", ...]
    confirmation_required: bool = False
    confirmation_message: str | None = None
    risk_level: str | None = None
    action_params: dict | None = None
```

### 3. 확인 카드 UI (`ConfirmationCard.jsx`)
- 리스크 레벨별 시각적 구분 (빨강/노랑/회색)
- 동작 설명, 파라미터 표시
- "취소" / "실행" 버튼

### 4. 슬래시 명령어 바로 실행
`/` 로 시작하는 명령어는 확인 없이 즉시 실행 (단, 고위험 액션 제외)

## 변경 파일

- `fastapi/app/schemas/tutor.py` (TutorRouteResponse 확장)
- `fastapi/app/api/routes/tutor.py` (_normalize_route_response 수정)
- `frontend/src/components/agent/ConfirmationCard.jsx` (신규)
- `frontend/src/hooks/useSlashCommands.js` (신규)
