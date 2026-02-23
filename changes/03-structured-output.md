# Phase 3: 구조화된 출력

## 문제

CTA 버튼이 고정된 옵션만 제공하여 대화 맥락에 맞지 않았고, 복잡한 작업 진행 상황을 알 수 없었습니다.

## 해결

### 1. 동적 CTA 버튼 (`_generate_cta_buttons`)
LLM이 응답 내용을 분석하여 맥락에 맞는 후속 액션 버튼 생성:
```python
async def _generate_cta_buttons(response_content: str, context: dict) -> list[CtaButton]:
    # "차트" 언급 → "다른 기간 보기"
    # "비교" 언급 → "더 비교하기"
    # 기본: "더 쉽게 설명해줘", "다음"
```

### 2. 할 일 목록 진행 표시 (`TodoProgress.jsx`)
복잡한 작업 시 진행 상황 표시:
- 총 개수 / 완료 개수
- 프로그래스 바
- 각 항목 상태 (대기/진행중/완료/에러)

### 3. SSE 이벤트 확장
```python
class TutorChatEvent(BaseModel):
    cta_buttons: list[CtaButton] | None = None
    todo_list: list[TodoItem] | None = None
```

## 변경 파일

- `fastapi/app/schemas/tutor.py` (CtaButton, TodoItem 추가)
- `fastapi/app/api/routes/tutor.py` (_generate_cta_buttons 추가)
- `frontend/src/components/agent/TodoProgress.jsx` (신규)
- `frontend/src/contexts/TutorUIContext.jsx` (todoList 상태 추가)
