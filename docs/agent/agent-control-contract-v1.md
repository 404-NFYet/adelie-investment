# Agent Control Contract v1

## 목적
- 프론트와 에이전트(LLM/백엔드)가 공통으로 이해하는 화면 상태 및 실행 가능 액션 계약을 정의한다.

## 요청 계약 (`context_text`)
`/api/v1/tutor/chat` 요청의 `context_text`는 문자열(JSON 직렬화)이며 다음 구조를 권장한다.

```json
{
  "mode": "home|stock|education|my",
  "context": {},
  "ui_snapshot": {
    "route": "/home",
    "mode": "home",
    "visible_sections": [],
    "selected_entities": {
      "stock_code": null,
      "stock_name": null,
      "date_key": null,
      "case_id": null
    },
    "filters": {
      "period": null,
      "tab": "home",
      "keyword": null
    },
    "portfolio_summary": null,
    "location_state": null,
    "captured_at": "ISO8601"
  },
  "action_catalog": [
    {
      "id": "nav_home",
      "label": "홈으로 이동",
      "risk": "low|high",
      "params_schema": {},
      "intent_keywords": []
    }
  ],
  "interaction_state": {
    "source": "agent_dock|home_page|portfolio_stock_detail|agent_canvas",
    "mode": "home",
    "route": "/home",
    "last_prompt": null,
    "focused_prompt": null,
    "control_phase": "idle|running|success|error",
    "control_active": false
  }
}
```

## 실행 정책
### Low risk (즉시 실행)
- 탭 이동/라우팅
- 기록/아카이브 진입
- 화면 필터/섹션 전환

### High risk (확인 필요)
- 매수/매도 관련 이동
- 외부 링크 오픈
- 데이터 변경/삭제

## SSE 응답 계약
기존 이벤트를 유지하며 아래 확장을 허용한다.

- `thinking`
- `tool_call`
- `text_delta`
- `visualization` (optional)
- `ui_action` (optional)
- `done`
- `error`

`done` 이벤트 권장 필드:
- `type: "done"`
- `session_id`
- `total_tokens`
- `model` (예: `gpt-4o-mini`)
- `sources` (optional)

## 프론트 fallback 규칙
- `ui_action` 이벤트가 없어도 동작해야 한다.
- `action_catalog` 기반으로 로컬 오케스트레이터가 실행 경로를 결정한다.
- 구조화 정보가 없으면 캔버스는 텍스트 우선 렌더링으로 표시한다.
