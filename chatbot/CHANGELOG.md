# Chatbot 수정사항 정리

> **기간**: 2026-02-25  
> **범위**: `chatbot/` 폴더 구조 개편 이후 수정사항  
> **적용 환경**: `chatbot/services/`, `fastapi/app/api/routes/`, `frontend/src/`

## 6. Hybrid Clarification Flow

### 개요
사용자의 모호한 질문에 대해 즉시 답변하는 대신, 의도를 명확히 하는 clarification 질문을 먼저 제시하는 하이브리드 흐름 추가.

### 변경 사항
- **`chatbot/agent/tutor_agent.py`**: clarification 분기 노드 추가 — 의도 분류 후 명확화 필요 시 선택지 제시
- **PR #36** 통합 머지 (1e856ab): hybrid clarification + 기존 가드레일/Chart-First 통합

### 동작 방식
```
사용자 질문 → 의도 분류
  ├─ 명확한 질문 → 기존 응답 파이프라인
  └─ 모호한 질문 → clarification 선택지 제시 → 사용자 선택 → 응답
```

## 1. 가드레일 — 문맥 인식 버그 수정

### 문제
가드레일이 사용자의 **단독 메시지**만 평가하고 있어, 페이지 문맥이나 대화 기록 없이는 `"지금 상황과 왜 비슷한지 더 자세하게 설명해줘"` 같은 후속 질문을 차단하는 문제가 있었습니다.

### 수정
- **`fastapi/app/api/routes/tutor.py`**: 가드레일 호출 시점을 `page_context` 및 `prev_msgs`를 불러온 **이후**로 이동
- **`chatbot/services/guardrail.py`** 및 **`chatbot/prompts/templates/guardrail.md`**: `guardrail_context`(페이지 문맥 + 직전 AI 답변)를 함께 전달받아 LLM이 대화 흐름 내 의도를 파악하고 `SAFE`로 올바르게 분류하도록 수정

```python
# 수정 전: 메시지만 전달
guardrail_result = await run_guardrail(request.message)

# 수정 후: 페이지 문맥 + 이전 대화 마지막 답변도 함께 전달
guardrail_result = await run_guardrail(request.message, context=guardrail_context)
```


## 2. 차트 분류 — Pydantic 유효성 검증 오류 수정

### 문제
사용자가 "셀트리온 최근 주가 차트 보여줘"와 같이 명시적으로 차트를 요청해도, `classify_chart_request`가 반환한 JSON이 `ChartClassificationResult` Pydantic 모델과 불일치하여 항상 `UNSUPPORTED`로 분기되었습니다.

### 수정
- **`chatbot/services/tutor_chart_generator.py`**: 분류 시스템 프롬프트에 반드시 지켜야 할 출력 JSON 스키마를 명시하도록 강화

```json
// 강제 출력 형식
{ "reasoning": "...", "chart_type": "line" }
```


## 3. Chart-First Architecture — 스트리밍 파이프라인 전면 재설계

### 문제
텍스트 응답이 차트보다 먼저 스트리밍되어 LLM이 "위에 차트가 이미 그려질 예정"을 인지하지 못하고 텍스트 기호(`|`, `*`)로 ASCII 차트를 직접 그리는 문제가 발생했습니다.

### 수정
**`fastapi/app/api/routes/tutor.py`에서 500줄의 스트리밍 로직을 제거**하고, 해당 로직을 `chatbot/services/tutor_engine.py`의 `generate_tutor_response_stream`으로 통합했습니다.

**신규 파이프라인 순서:**

```
1. 시각화 필요 여부 판단 (should_auto_visualize)
2. [차트 필요 시] 차트 종류 분류 → Plotly JSON 생성 → event: visualization 전송
3. 차트 생성 결과에 따라 LLM 시스템 프롬프트 동적 주입
   ├─ 성공: "ASCII 차트 절대 금지, 차트 해석만 제공하라"
   └─ 실패(UNSUPPORTED): "텍스트로 수치와 흐름을 설명하라"
4. 메인 LLM 텍스트 스트리밍 시작
```

**지원하지 않는 차트 요청 시 fallback 메시지 (⚠️ 미완성):**
```
지금은 해당 시각화를 지원하지 않아요. 빠르게 업데이트하도록 할게요! 🐧
```

> [!WARNING]
> **수정 필요**: fallback 메시지가 아직 프론트엔드에서 올바르게 표시되지 않고 있음. `event: text_delta`로 전송 시 기존 스트리밍 텍스트와 처리 방식이 충돌하거나, `TutorContext.jsx`의 `action_type: 'visualizing'` 이벤트 핸들러가 없어 로딩 표시 없이 곧바로 fallback이 출력되는 문제 존재. 추가 조사 및 수정 예정.


## 4. Claude API 의존성 제거 — 차트 JSON 생성 버그 수정

### 문제
`generate_chart_json`이 Claude API(`claude-3-5-haiku-20241022`)를 우선 호출하는데, API 키가 없거나 미지원 모델로 인해 404 오류가 발생하여 차트가 항상 생성되지 않았습니다.

```
# 오류 로그
Chart JSON generation failed: Error code: 404
{'error': {'message': 'model: claude-3-5-haiku-20241022'}}
[Chart-First] chart_json generated: False
```

### 수정
- **`chatbot/services/tutor_chart_generator.py`**: Anthropic 의존성(`import anthropic`) **완전 제거**
- 차트 분류 및 JSON 생성 모두 **OpenAI `gpt-4o-mini`** 단독 사용으로 변경

```python
# 수정 전: Claude 우선, OpenAI 폴백 (Claude 404로 폴백 불가 상태)
claude_api_key = os.getenv("CLAUDE_API_KEY") or get_settings().ANTHROPIC_API_KEY
if claude_api_key:
    client = anthropic.AsyncAnthropic(...)  # ← 404 오류 발생!

# 수정 후: OpenAI 전용
o_client = AsyncOpenAI(api_key=get_settings().OPENAI_API_KEY)
```

**수정 후 로그:**
```
Chart JSON generated successfully: type=line, traces=2  ✅
[Chart-First] chart_json generated: True               ✅
```


## 5. 차트 메시지 순서 오류 수정 (Frontend)

### 문제
백엔드에서 차트 이벤트(`event: visualization`)가 텍스트보다 먼저 전송되어도, `TutorContext.jsx`가 이미 생성한 텍스트 말풍선(`assistantMessage`) 뒤에 차트를 추가(`push`)하여 UI 상에서 **차트가 텍스트 아래에** 나타났습니다.

```
표시 순서 (수정 전): [user] → [텍스트 답변] → [📈차트]  ← 잘못된 순서
표시 순서 (목표):    [user] → [📈차트] → [텍스트 답변]
```

### 수정
- **`frontend/src/contexts/TutorContext.jsx`**: 시각화 메시지를 배열 맨 뒤에 `push`하는 대신, `assistantMessage.id`를 기준으로 **그 앞에 `splice`로 삽입**하도록 변경

```javascript
// 수정 전
setMessages((prev) => [...prev, vizMessage]);  // ← 항상 맨 뒤에 추가

// 수정 후
setMessages((prev) => {
  const idx = prev.findIndex((m) => m.id === assistantMessage.id);
  if (idx === -1) return [...prev, vizMessage];
  const next = [...prev];
  next.splice(idx, 0, vizMessage);  // ← 텍스트 말풍선 앞에 삽입
  return next;
});
```


## 변경 파일 요약

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `chatbot/services/tutor_engine.py` | **대폭 수정** | `generate_tutor_response_stream` 신규 구현 (Chart-First 파이프라인 포함) |
| `chatbot/services/tutor_chart_generator.py` | **구조 개편** | 챗봇 모듈로 이동 및 OpenAI gpt-4o-mini 단독 사용 체제 안정화 |
| `chatbot/services/guardrail.py` | **버그 수정** | `context` 파라미터 추가 및 프롬프트 반영 |
| `fastapi/app/api/routes/tutor.py` | **경량화** | 인라인 스트리밍 로직 제거, `tutor_engine.py`로 위임 |
| `frontend/src/contexts/TutorContext.jsx` | **버그 수정** | 차트 메시지 삽입 위치 수정 (`push` → `splice`) |
