# 챗봇 개선 계획

> 작성일: 2026-02-26
> 브랜치: dev-final/chatbot

---

## 개요

1. **모의투자 탭 화면 컨텍스트 추가** — Portfolio 페이지에서도 챗봇이 현재 화면 데이터를 인식
2. **시각화 파이프라인 상태 메시지 개선** — 시각화 시도/불가 여부를 먼저 텍스트로 알림
3. **시각화 push-down 버그 수정** — 차트 생성 후 텍스트 답변이 위에 렌더링되는 버그 수정

---

## 현재 구조 분석

### 화면 컨텍스트 흐름
- `Narrative.jsx` → `setContextInfo({ stepTitle, stepContent })` → `TutorContext`의 `contextInfo` → 백엔드 `context_text`로 전달
- `Portfolio.jsx`는 `useTutor`를 사용하지 않아 컨텍스트 미전달

### 시각화 파이프라인 현재 순서 (`tutor_engine.py`)
1. `thinking` 이벤트 emit
2. `classify_chart_request` 실행 → 분류 결과 확인
3. SUPPORTED: `action` 이벤트 emit (❌ 프론트엔드에서 완전 무시됨) → 차트 생성 → `visualization` 이벤트 emit
4. UNSUPPORTED: `text_delta`로 fallback 메시지 emit
5. LLM 텍스트 응답 스트리밍

### 시각화 push-down 버그 원인 (`TutorContext.jsx`)
- `sendMessage` 시작 시 빈 `assistantMessage`를 즉시 messages 배열에 추가 (L122-129)
- 사용자는 하단에 빈 스트리밍 버블을 먼저 봄
- `visualization` 이벤트 도착 시 빈 `assistantMessage` **앞에** 삽입 (`splice(idx, 0, vizMessage)`)
- `TutorModal`의 `useEffect`가 messages 변경마다 `messagesEndRef.scrollIntoView()` 호출
- **결과**: 스크롤이 항상 맨 아래(assistantMessage)를 가리키기 때문에 visualization이 viewport 밖으로 밀려나고 텍스트만 보임

---

## 변경 계획

### 변경 파일 요약

| 파일 | 변경 내용 |
|---|---|
| `chatbot/services/tutor_engine.py` | `action` → `viz_intent` 이벤트 타입 변경 |
| `frontend/src/contexts/TutorContext.jsx` | `viz_intent` 핸들러 추가, `assistantMessage` lazy 생성으로 변경 |
| `frontend/src/components/tutor/TutorModal.jsx` | TypingIndicator 조건 수정 |
| `frontend/src/pages/Portfolio.jsx` | `useTutor` 컨텍스트 연동, 포트폴리오 데이터 컨텍스트 주입 |

---

### Task 1: `chatbot/services/tutor_engine.py` — viz_intent 이벤트 교체

**변경 위치**: `generate_tutor_response_stream` 함수 내 Chart-First 파이프라인 블록

**SUPPORTED 케이스** (현재 `action` 이벤트 → 무시됨):
```python
# 변경 전
yield f"event: action\ndata: {json.dumps({'action_type': 'visualizing', 'message': '데이터 시각화 중이에요. 잠시만 기다려주세요...'})}\n\n"

# 변경 후
yield f"event: viz_intent\ndata: {json.dumps({'type': 'viz_intent', 'content': '📊 차트를 그려볼게요! 잠시만 기다려주세요.'})}\n\n"
```

**UNSUPPORTED 케이스**: 기존 `text_delta` fallback 유지 (이미 잘 동작함)

---

### Task 2: `frontend/src/contexts/TutorContext.jsx` — Lazy assistantMessage + viz_intent 핸들러

#### 2-1. `assistantMessage` 즉시 생성 제거

```js
// 변경 전 (sendMessage 시작 시 즉시 추가)
const assistantMessage = {
  id: Date.now() + 1,
  role: 'assistant',
  content: '',
  timestamp: new Date().toISOString(),
  isStreaming: true,
};
setMessages((prev) => [...prev, assistantMessage]);

// 변경 후 (ID만 준비, 메시지는 lazy 생성)
const assistantMsgId = Date.now() + 1;
let assistantMsgCreated = false;
```

#### 2-2. `viz_intent` 이벤트 핸들러 추가 (thinking, tool_call 핸들러 다음에 추가)

```js
if (data.type === 'viz_intent') {
  setAgentStatus({ phase: 'tool_call', text: '차트를 생성하고 있어요...' });
  const statusMessage = {
    id: Date.now() + Math.random(),
    role: 'assistant',
    content: data.content,  // "📊 차트를 그려볼게요! 잠시만 기다려주세요."
    timestamp: new Date().toISOString(),
    isStreaming: false,
    isVizStatus: true,
  };
  setMessages((prev) => [...prev, statusMessage]);
  continue;
}
```

#### 2-3. 첫 `text_delta` 도착 시 assistantMessage lazy 생성

```js
if (data.content) {
  if (!fullContent) {
    setAgentStatus({ phase: 'answering', text: '답변을 생성 중입니다.' });
  }
  fullContent += data.content;
  pendingFlush = true;

  // lazy 생성: 첫 텍스트 도착 시 메시지 버블 생성
  if (!assistantMsgCreated) {
    assistantMsgCreated = true;
    setMessages((prev) => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      content: fullContent,
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }]);
    lastFlushTime = Date.now();
    pendingFlush = false;
  }
}
```

#### 2-4. 이후 update/flush 로직에서 `assistantMessage.id` → `assistantMsgId` 로 교체

- `setMessages(prev => prev.map(m => m.id === assistantMsgId ? {...m, content: fullContent} : m))`
- visualization 삽입 시: `assistantMsgCreated`가 false이면 `[...prev, vizMessage]` (append), true이면 기존 splice 유지

#### 2-5. 에러/완료 처리 방어 코드

error 및 catch 블록에서 `assistantMessage`가 아직 없을 경우 새로 생성:
```js
// error 타입 처리
if (data.type === 'error' && data.error) {
  if (!assistantMsgCreated) {
    assistantMsgCreated = true;
    setMessages((prev) => [...prev, {
      id: assistantMsgId,
      role: 'assistant',
      content: `오류: ${data.error}`,
      timestamp: new Date().toISOString(),
      isStreaming: false,
      isError: true,
    }]);
  } else {
    setMessages((prev) => prev.map((m) =>
      m.id === assistantMsgId
        ? { ...m, content: `오류: ${data.error}`, isStreaming: false, isError: true }
        : m
    ));
  }
}
```

스트림 종료 시 마무리:
```js
// 스트림 종료 후 최종 업데이트
if (assistantMsgCreated) {
  setMessages((prev) =>
    prev.map((m) => (m.id === assistantMsgId ? { ...m, content: fullContent, isStreaming: false } : m))
  );
}
```

#### 변경 후 렌더 순서

| 단계 | messages 배열 상태 |
|---|---|
| sendMessage 시작 | `[user]` |
| viz_intent 도착 | `[user, statusBubble("📊 차트를 그려볼게요!")]` |
| visualization 도착 | `[user, statusBubble, visualization]` |
| 첫 text_delta 도착 | `[user, statusBubble, visualization, assistant("LLM 텍스트...")]` |
| 스트리밍 완료 | `[user, statusBubble, visualization, assistant("LLM 텍스트 전체", isStreaming: false)]` |

---

### Task 3: `frontend/src/components/tutor/TutorModal.jsx` — TypingIndicator 조건 수정

**현재:**
```jsx
{isLoading && messages.length > 0 && messages[messages.length - 1]?.role === 'user' && <TypingIndicator />}
```

**변경 후:**
```jsx
{isLoading && !messages.some((m) => m.isStreaming) && <TypingIndicator />}
```

- `assistantMessage`가 lazy 생성되는 동안 (isStreaming이 없는 상태) TypingIndicator 표시
- `viz_intent` 버블이 마지막에 와도 로딩 표시 유지
- assistantMessage가 생성되어 `isStreaming: true`가 되면 TypingIndicator 자동 사라짐

---

### Task 4: `frontend/src/pages/Portfolio.jsx` — 모의투자 컨텍스트 추가

**import 추가:**
```jsx
import { useTutor } from '../contexts/TutorContext';
```

**컴포넌트 내부에 추가:**
```jsx
const { setContextInfo } = useTutor();

// 탭/포트폴리오 데이터 변경 시 컨텍스트 업데이트
useEffect(() => {
  const tabNames = { holdings: '보유 종목', trading: '자유 매매', leaderboard: '나의 랭킹' };
  const tabLabel = tabNames[activeTab] || '보유 종목';

  const holdings = displayPortfolio.holdings || [];
  const holdingsText = holdings.length > 0
    ? holdings.map(h =>
        `${h.stock_name}(${h.stock_code}): ${h.quantity}주, 평균매수가 ${formatKRW(h.avg_buy_price)}, 현재가 ${formatKRW(h.current_price || 0)}, 수익률 ${Number(h.profit_loss_pct || 0).toFixed(2)}%`
      ).join('\n')
    : '보유 종목 없음';

  const stepContent = [
    `[모의투자 포트폴리오 - ${tabLabel}]`,
    `총 자산: ${formatKRW(displayPortfolio.total_value || 0)}`,
    `보유 현금: ${formatKRW(displayPortfolio.current_cash || 0)}`,
    `투자 금액: ${formatKRW((displayPortfolio.total_value || 0) - (displayPortfolio.current_cash || 0))}`,
    `총 손익: ${Number(displayPortfolio.total_profit_loss || 0) >= 0 ? '+' : ''}${formatKRW(displayPortfolio.total_profit_loss || 0)} (${Number(displayPortfolio.total_profit_loss_pct || 0).toFixed(2)}%)`,
    `\n보유 종목:\n${holdingsText}`,
  ].join('\n');

  setContextInfo({
    stepTitle: `모의투자 - ${tabLabel}`,
    stepContent,
  });

  return () => setContextInfo(null);
}, [activeTab, displayPortfolio, setContextInfo]);
```

- **activeTab 변경 시**: stepTitle이 "모의투자 - 보유 종목" / "모의투자 - 자유 매매" / "모의투자 - 나의 랭킹"으로 업데이트
- **displayPortfolio 변경 시**: 포트폴리오 새로고침 후 최신 데이터 반영
- **페이지 이탈 시**: `setContextInfo(null)` cleanup으로 컨텍스트 초기화
- TutorModal 헤더의 "현재 보고 있는 화면" 표시도 자동 업데이트 (`contextInfo?.stepTitle`)

---

## 기대 효과

1. **모의투자 탭**: 챗봇이 "내 포트폴리오 분석해줘", "삼성전자 수익률이 왜 이래?" 등의 질문에 현재 화면 데이터를 참고하여 답변 가능
2. **시각화 상태 메시지**: 사용자가 차트 생성 시도 여부를 즉시 텍스트로 확인 가능
3. **렌더 순서 정상화**: 상태 메시지 → 차트 → 텍스트 설명 순서로 자연스럽게 표시
4. **스크롤 버그 해소**: 차트가 viewport 밖으로 밀려나지 않고 올바른 위치에 유지

---

## 버그 픽스 1차

> 추가일: 2026-02-26

### BF-1: 3D 시각화 요청 시 `unsupported` 대신 `line` 차트가 그려지는 버그

**재현 입력 예시**: "삼성전자 주가와 반도체 장비 수요를 한 화면에 3D로 그려줘"

**기대 동작**: "해당 시각화를 지원하지 않아요" 안내 메시지 출력

**실제 동작**: line 차트가 그려짐

#### 근본 원인

`classify_chart_request` 프롬프트가 "3D 모델링, 비디오 생성"은 `unsupported`로 명시하지만, **"3D 차트/그래프"** 는 별도 언급이 없음.
GPT-4o-mini가 "삼성전자 주가" 키워드를 보고 "주가 추이 = line" 으로 우선 매핑하고 3D 수식어를 무시함.

#### 수정 계획

**A. `chatbot/services/tutor_engine.py` — 키워드 선제 필터 추가** (LLM 판단 이전에 차단)

```python
# classify_chart_request 호출 전에 삽입
UNSUPPORTED_VIZ_KEYWORDS = ['3d', '3차원', '입체', '애니메이션', '동영상', 'vr', 'ar']
if should_viz and any(kw in request.message.lower() for kw in UNSUPPORTED_VIZ_KEYWORDS):
    # UNSUPPORTED 경로로 직접 분기 (LLM 호출 없이)
    classification = ChartClassificationResult(
        reasoning="3D/애니메이션 시각화는 미지원",
        chart_type=ChartType.UNSUPPORTED,
    )
    # 이후 기존 UNSUPPORTED 처리 로직 그대로 실행
```

**B. `chatbot/services/tutor_chart_generator.py` — 분류 프롬프트 보강** (이중 방어)

```python
# 기존
"질문이 위 11가지 형태에 전혀 맞지 않거나 3D 모델링, 비디오 생성 등 시각화 불가능한 내용일 경우 'unsupported'로 분류하세요."

# 변경
"다음 경우 반드시 'unsupported'로 분류하세요: "
"① 3D 차트, 입체 그래프, 3차원 시각화 요청 (3D 수식어가 있으면 무조건 unsupported) "
"② 애니메이션, 동영상, VR/AR 생성 요청 "
"③ 위 11가지 차트 유형으로 표현 불가능한 내용"
```

#### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `chatbot/services/tutor_engine.py` | `classify_chart_request` 호출 전 키워드 선제 필터 추가 |
| `chatbot/services/tutor_chart_generator.py` | 분류 프롬프트 `unsupported` 기준 구체화 |

---

### BF-2: 시각화 후 텍스트 분석이 출력되지 않는 버그

**재현 상황**: 차트가 성공적으로 그려진 후, 해당 차트에 대한 분석/설명 텍스트가 나오지 않음

**기대 동작**: 차트 렌더링 → 차트 내용 기반 분석 텍스트 스트리밍

**실제 동작**: 차트만 렌더링되고 텍스트 답변 없음 (또는 매우 빈약)

#### 근본 원인

`tutor_engine.py`의 Chart-First 파이프라인에서 **차트 데이터(`chart_json`)를 텍스트 생성 LLM에게 전달하지 않음**.
LLM은 "차트가 그려졌다"는 사실만 알 뿐 실제 수치/추이를 모르기 때문에,
`chart_system_prompt`의 "지지선/저항선 해석을 제공하세요" 지침을 따를 수 없어 최소한의 출력 또는 침묵으로 이어짐.

#### 수정 계획

**A. `chatbot/services/tutor_engine.py` — 차트 데이터 요약을 LLM 컨텍스트에 주입**

```python
# chart_json 생성 직후 (visualization 이벤트 emit 다음)
if chart_json and "data" in chart_json:
    import json as _json
    chart_data_summary = _json.dumps(chart_json["data"], ensure_ascii=False)[:800]
    chart_system_prompt += (
        f"\n\n[생성된 차트 데이터 요약 — 이 수치를 기반으로 분석하세요]\n{chart_data_summary}"
    )
```

**B. `chart_system_prompt` 분석 지침 3단계로 구체화**

```python
# 기존: "오직 줄글 해석만 제공하세요" (너무 제한적)
# 변경: 명확한 3단계 분석 요구

chart_system_prompt = (
    "[[CRITICAL INSTRUCTION]]\n"
    "이미 UI 상에 인터랙티브 차트(Plotly)가 성공적으로 렌더링되었습니다.\n"
    "텍스트로 차트를 다시 그리거나(|, ─, * 등 ASCII 기호 사용 금지), '아래 차트를 보세요' 같은 중복 멘트는 하지 마세요.\n\n"
    "반드시 아래 3단계 구조로 분석을 제공하세요:\n"
    "1. **차트 핵심 수치 요약**: 최고/최저값, 주요 변곡점, 전체 추이 방향을 2~3문장으로 서술\n"
    "2. **투자자 관점 시사점**: 위 수치가 의미하는 바, 주의해야 할 신호, 비교 관점\n"
    "3. **메타인지 역질문**: 사용자가 이 차트에서 더 궁금해할 만한 부분을 1가지 질문으로 유도\n"
)
```

#### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `chatbot/services/tutor_engine.py` | ① `chart_json` 데이터 요약을 LLM 컨텍스트에 주입<br>② `chart_system_prompt` 3단계 분석 구조로 개선 |

---

### BF-3: 시각화 메시지에 출처 정보가 표시되지 않는 문제

**재현 상황**: 텍스트 답변에는 "N개 출처" 배지가 표시되지만, 차트 버블에는 출처가 표시되지 않음

**기대 동작**: 차트 버블 하단에도 `SourceBadge` 표시 (텍스트 버블과 동일한 출처 공유)

#### 근본 원인

- `TutorContext.jsx`: `done` 이벤트의 `sources`를 `assistantMsgId`(텍스트 메시지)에만 부착, `vizMessage`에는 미부착
- `MessageBubble.jsx`: `VisualizationMessage` 컴포넌트에 `SourceBadge` 렌더링 없음

#### 수정 계획

**A. `frontend/src/contexts/TutorContext.jsx` — viz 메시지에 sources 부착**

```js
// visualization 이벤트 처리 시 vizMsgId 추적
let vizMsgId = null;
// ...
if (data.type === 'visualization' && ...) {
  const vizMessage = { id: Date.now() + Math.random(), ... };
  vizMsgId = vizMessage.id;  // ID 저장
  // ...
}

// done 이벤트에서 vizMsgId에도 sources 부착
if (data.type === 'done' && data.sources) {
  pendingSources = data.sources;
  setMessages((prev) =>
    prev.map((m) => {
      if (m.id === assistantMsgId || m.id === vizMsgId) {
        return { ...m, sources: data.sources };
      }
      return m;
    })
  );
}
```

**B. `frontend/src/components/tutor/MessageBubble.jsx` — `VisualizationMessage`에 `SourceBadge` 추가**

```jsx
// VisualizationMessage 컴포넌트 return 블록 하단에 추가
{hasChart && (
  <button onClick={() => setExpanded(!expanded)} ...>
    {expanded ? '축소' : '확대'}
  </button>
)}
{message.sources && message.sources.length > 0 && (
  <SourceBadge sources={message.sources} />
)}
```

#### 변경 파일

| 파일 | 변경 내용 |
|---|---|
| `frontend/src/contexts/TutorContext.jsx` | viz 메시지 ID 추적 + `done` 이벤트 시 sources 부착 |
| `frontend/src/components/tutor/MessageBubble.jsx` | `VisualizationMessage`에 `SourceBadge` 렌더링 추가 |
