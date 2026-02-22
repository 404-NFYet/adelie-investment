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
- `model` (예: `gpt-5-mini`)
- `sources` (optional)
- `search_used` (optional)
- `response_mode` (optional, `plain | canvas_markdown`)
- `structured` (optional)

## LLM 호출 경로 비교 (기존 vs Responses API)
현재 `/api/v1/tutor/chat`는 `Responses API`를 우선 사용하고, 실패 시 기존 `chat.completions` 스트리밍으로 폴백한다.

| 항목 | 기존 (`chat.completions`) | 현재 우선 경로 (`responses`) |
|---|---|---|
| 입력 구조 | `messages: [{role, content}]` | `input: [{role, content}]` |
| 스트리밍 단위 | `chunk.choices[0].delta.content` | 이벤트 기반 (`response.output_text.delta`) |
| 도구 호출 | 튜터 경로에서 제한적 | `tools`로 웹검색 등 확장 용이 |
| 웹검색 옵션 | 사실상 미지원(안내 메시지 폴백) | `use_web_search=true` 시 `web_search_preview` 사용 |
| SSE 매핑 | 텍스트 델타 중심 | 이벤트 매핑으로 `text_delta/tool_call/done/error` 변환 |
| 완료 메타 | 토큰/모델 제한적 | `model`, `search_used`, `response_mode`, `structured` 확장 |
| 구조화 추출 | 별도 없음 | `structured_extract=true`일 때 완료 후 보조 추출 |
| 실패 처리 | 에러 전파 | Responses 실패 시 chat.completions 자동 폴백 |

## Responses API -> 프론트 SSE 이벤트 매핑
- `response.output_text.delta` -> `text_delta`
- `*web_search*`/`*tool*` 이벤트 -> `tool_call` (step)
- `response.completed` -> `done`
- `response.error`/`error` -> `error`

프론트는 `event:` 라인과 `data.type` 둘 다 읽어야 하며, 누락 시 이벤트명을 타입으로 보정한다.

## 왜 바꿨는지 (운영 관점)
- `gpt-5-mini`에서 델타 스트리밍 안정성과 이벤트 가시성을 높이기 위해
- 웹 검색 ON/OFF를 사용자 제어형으로 붙이기 위해
- 캔버스 markdown 응답 + 완료 후 구조화 요약을 동시에 지원하기 위해

## 디버깅 체크포인트
- 텍스트가 안 흐르면:
  - Responses 이벤트에서 `response.output_text.delta` 수신 여부 확인
  - 폴백 여부 로그(`responses_api_fallback`) 확인
- 검색이 안 붙으면:
  - 요청의 `use_web_search` 값 확인
  - 완료 이벤트 `done.search_used` 확인
- 캔버스 구조화가 비면:
  - `response_mode=canvas_markdown` + `structured_extract=true` 확인
  - 실패 시 markdown 원문 렌더가 fallback으로 유지되는지 확인

## 프론트 fallback 규칙
- `ui_action` 이벤트가 없어도 동작해야 한다.
- `action_catalog` 기반으로 로컬 오케스트레이터가 실행 경로를 결정한다.
- 구조화 정보가 없으면 캔버스는 텍스트 우선 렌더링으로 표시한다.
