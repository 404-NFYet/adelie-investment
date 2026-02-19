# 챗봇 시스템 구조 문서

> 최종 수정일: 2026-02-19  
> 작업 범위: 가드레일 고도화 / 시각화 모델 변경 / Interface 3 동적 질문 선택지 구현

---

## 📁 관련 파일

| 파일 | 역할 |
|------|------|
| `fastapi/app/services/guardrail.py` | LangGraph 가드레일 그래프 정의 |
| `fastapi/app/api/routes/tutor.py` | 메인 응답 생성 로직 + 추천 질문 엔드포인트 |
| `fastapi/app/services/tutor_engine.py` | 컨텍스트 수집 헬퍼 함수 모음 (직접 호출 안 됨) |
| `frontend/src/contexts/TutorContext.jsx` | 챗봇 상태 관리 + 추천 질문 API 연동 |
| `frontend/src/pages/Narrative.jsx` | Interface 3 페이지 + 컨텍스트 주입 |
| `frontend/src/components/tutor/TutorModal.jsx` | 챗봇 UI + 추천 질문 렌더링 |

---

## 🔗 1. 가드레일 시스템 (`guardrail.py`)

LangGraph로 구현된 **4-카테고리 CoT+퓨샷 입력 분류기**입니다.  
사용자 메시지가 허용 가능한지 판별하고, 차단 시 사유별 맞춤 메시지를 반환합니다.

### 그래프 구조

```
START → [classify_input] → decide_route() → END
                                ├─ SAFE      → END (허용)
                                ├─ ADVICE    → END (차단: 투자 자문 거절)
                                ├─ OFF_TOPIC → END (차단: 서비스 범위 안내)
                                └─ MALICIOUS → END (차단: 보안 경고)
```

### 상태(GuardrailState) 변수

```
GuardrailState
├── message    : str   사용자 입력 메시지
├── decision   : str   "SAFE" | "ADVICE" | "OFF_TOPIC" | "MALICIOUS"
├── reasoning  : str   LLM이 분류 근거를 먼저 서술하는 CoT 텍스트
└── is_allowed : bool  SAFE 여부
```

### 카테고리 분류 기준

| 카테고리 | 해당 케이스 | 처리 |
|---------|-----------|------|
| `SAFE` | 거시경제, 기업 실적, 시장 동향 등 정상 금융 정보 | ✅ 허용 |
| `ADVICE` | 특정 종목 매수/매도/보유 추천 등 투자 자문 | 🚫 금융투자업 규정 위반 안내 |
| `OFF_TOPIC` | 금융과 무관한 일상 대화, 타 도메인 질문 | 🚫 서비스 범위 안내 |
| `MALICIOUS` | 프롬프트 인젝션, 욕설, 시스템 탈취 시도 | 🚫 보안 경고 |

### LLM 출력 형식 (JSON 강제)

```json
{
  "reasoning": "사용자가 특정 종목 매수를 요청했으므로...",
  "decision": "ADVICE"
}
```

CoT 구조로 `reasoning`(근거)을 먼저 생성하게 하여 섣부른 허용 bias를 억제합니다.

### `run_guardrail()` 반환값

| is_allowed | block_message | decision |
|-----------|--------------|---------|
| `True` | `""` | `"SAFE"` |
| `False` | 투자 자문 거절 안내문 | `"ADVICE"` |
| `False` | 범위 외 안내문 | `"OFF_TOPIC"` |
| `False` | 보안 경고문 | `"MALICIOUS"` |

> **Fail-closed 정책**: LLM 파싱 실패 시 `OFF_TOPIC` 기본 처리 (차단 우선)

---

## 🔄 2. 전체 요청 처리 흐름 (`tutor.py`)

```
[프론트엔드]
  POST /api/v1/tutor/chat
        │
        ▼
[tutor.py] generate_tutor_response()
        │
        ▼
  Step 0: LangGraph 가드레일
    run_guardrail(message) → GPT-4o-mini CoT 4-카테고리 분류
    차단(ADVICE/OFF_TOPIC/MALICIOUS) → 카테고리별 메시지 SSE 전송 후 종료
        │ SAFE
        ▼
  Step 1: 컨텍스트 수집
    - Glossary DB 용어 조회
    - HistoricalCase / BrokerReport DB 검색
    - 종목 감지 + pykrx 주가/재무 지표 조회
    - 현재 페이지 컨텍스트 (context_type / context_id)
    - 포트폴리오 컨텍스트 (로그인 사용자)
        │
        ▼
  Step 2: 시스템 프롬프트 구성
    - 난이도별 기본 프롬프트 (beginner / elementary / intermediate)
    - 페이지/포트폴리오/용어/사례/주가 컨텍스트 추가
        │
        ▼
  Step 3: 이전 대화 로드 (DB, 최대 20개)
        │
        ▼
  Step 4: GPT-4o-mini 스트리밍 응답
    - SSE event: text_delta (청크 단위)
    - 300초 타임아웃 / 클라이언트 연결 해제 감지
        │
        ▼
  Step 5: DB 저장 (TutorSession + TutorMessage)
        │
        ▼
  Step 6: 자동 시각화 (조건부)
    - stock 감지 or should_auto_visualize() == True 일 때
    - 입력: 챗봇 응답 전문 앞 500자
    - 모델: Claude Sonnet 4.6 (claude-sonnet-4-6)
    - 출력: {"data": [...], "layout": {...}} Plotly JSON
    - SSE event: visualization
        │
        ▼
  Step 7: 완료
    - SSE event: done (session_id, total_tokens, sources, guardrail)
```

---

## 💬 3. Interface 3 동적 질문 선택지

내러티브(Interface 3) 페이지를 읽는 사용자에게, 해당 페이지 내용 기반 질문 3개를 챗봇 초기화면에 자동 제공합니다.

> **기존 문제**: `quickQuestions` 배열에 3개 질문이 하드코딩되어 모든 페이지에서 동일하게 노출됨.

### 전체 데이터 흐름

```
사용자가 /narrative/{caseId} 페이지 진입
        │
        ▼
[Narrative.jsx]
  setContextInfo({ type: 'case', id: caseId })
        │
        ▼ (TutorContext useEffect 자동 감지)
[TutorContext.jsx]
  GET /api/v1/tutor/suggestions?context_type=case&context_id={N}
  → suggestedQuestions 상태 배열 업데이트
        │
        ▼ (사용자가 챗봇 열기)
[TutorModal.jsx]
  messages.length === 0이면 suggestedQuestions 렌더링
  버튼 클릭 → sendMessage(질문, difficulty) → 대화 시작
        │
        ▼ (다른 페이지 이동 시)
[Narrative.jsx] unmount cleanup
  setContextInfo(null)
  → suggestedQuestions = []  (다른 페이지에서는 선택지 미표시)
```

### 신규 API 엔드포인트

- **경로**: `GET /api/v1/tutor/suggestions`
- **쿼리 파라미터**:

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `context_type` | str | `"case"`만 처리. 그 외 → 빈 배열 반환 |
| `context_id` | int | `historical_cases` 테이블의 케이스 ID |

- **처리 순서**:
  1. `historical_cases.title`, `summary` 조회
  2. GPT-4o-mini → 초보 투자자용 질문 3개 생성 (JSON 배열 출력 강제)
  3. 파싱 후 반환

- **출력**: `{ "questions": ["질문1", "질문2", "질문3"] }`
- **오류 처리**: DB/LLM 실패 시 `{"questions": []}` 반환 → UI에 선택지 미표시

### 프론트엔드 파일별 변경

#### `Narrative.jsx`

| 항목 | 내용 |
|------|------|
| 추가 import | `useTutor` |
| 추가 동작 | 내러티브 로드 성공 시 `setContextInfo({ type: 'case', id: caseId })` 호출 |
| cleanup | 페이지 이탈 시 `setContextInfo(null)` 자동 실행 |

#### `TutorContext.jsx`

| 항목 | 내용 |
|------|------|
| 신규 상태 | `suggestedQuestions: string[]` (기본값 `[]`) |
| 신규 `useEffect` | `contextInfo` 변경 감지 → suggestions API 호출 → 상태 갱신 |
| Context 노출 | `value` 객체에 `suggestedQuestions` 추가 |

#### `TutorModal.jsx`

| 항목 | 기존 | 변경 후 |
|------|------|---------|
| 질문 출처 | 하드코딩 `quickQuestions` 배열 | `useTutor()`의 `suggestedQuestions` |
| 표시 조건 | 항상 표시 | `suggestedQuestions.length > 0`일 때만 |
| 고정 버튼 | "급등주 차트 보기" 고정 | 제거 |

---

## 📊 4. 주요 설정 요약

| 항목 | 값 |
|------|----|
| 가드레일 모델 | `gpt-4o-mini` (temperature=0, max_tokens=256) |
| 가드레일 방식 | CoT + 4-퓨샷, JSON 출력 강제 |
| 응답 생성 모델 | `gpt-4o-mini` (max_tokens=1000, stream=True) |
| 시각화 모델 | `claude-sonnet-4-6` (max_tokens=2000, Anthropic SDK) |
| 추천 질문 모델 | `gpt-4o-mini` (temperature=0.7, max_tokens=300) |
| 이전 대화 로드 | 최대 20개 메시지 |
| 스트리밍 타임아웃 | 300초 |
| 가드레일 실패 시 | fail-closed (OFF_TOPIC 처리) |
| Rate Limit | 10회 / 분 |

---

## ⚠️ 5. 참고 사항

### `tutor_engine.py` 현황

`tutor_engine.py`의 `generate_tutor_response()`는 **실제로 호출되지 않습니다.**  
`tutor.py` 라우터에서 import하여 사용하는 헬퍼 함수들만 사용됩니다:

```python
from app.services.tutor_engine import (
    _collect_glossary_context,
    _collect_db_context,
    _collect_stock_context,
    get_difficulty_prompt,
)
```

### 인라인 가드레일 (시스템 프롬프트)

- LangGraph 가드레일 = **하드 블로킹** (응답 자체를 중단)
- 시스템 프롬프트 가드레일 = **소프트 가이드** (LLM 행동 지침)

두 가드레일이 이중으로 작동합니다.

---

## ✅ 6. 검증 결과 (2026-02-19)

`make dev` 실행 후 백엔드 로그에서 실제 동작 확인:

```
SELECT title, summary FROM historical_cases WHERE id = 143
GET /api/v1/tutor/suggestions?context_type=case&context_id=143  →  200 OK
```

- DB 조회 및 GPT-4o-mini 질문 생성 정상 동작
- Interface 3 페이지 챗봇에서 페이지 맞춤 질문 3개 표시 확인
- 다른 페이지에서는 질문 선택지 미표시 확인
