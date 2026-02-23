# Phase 4: 모델/프롬프트/컨텍스트 개선

## 문제

- 이전 모델(`gpt-4o-mini`)의 응답 품질 이슈
- 대화가 길어지면 맥락을 잃어버림
- 톤 일관성 부족

## 해결

### 1. 모델 업그레이드
```python
TUTOR_CHAT_MODEL: str = "gpt-4.1-mini"
TUTOR_ROUTE_MODEL: str = "gpt-4.1-mini"
TUTOR_MAX_TOKENS: int = 2000  # 기존 대비 증가
```

### 2. 컨텍스트 관리 개선
```python
TUTOR_CONTEXT_MAX_CHARS: int = 8000  # 토큰 기반 슬라이딩 윈도우
TUTOR_AUTO_SUMMARIZE_TURNS: int = 10  # 10턴 이후 자동 요약
```

### 3. 아델리 톤 통합
```python
ADELIE_TONE = """
당신은 아델리(Adelie), 친근하면서도 전문적인 투자 교육 AI입니다.
- 친근한 어투 (반말 X, 존댓말 O)
- 이모지 적절히 활용
- 복잡한 개념은 비유로 설명
- 항상 긍정적이고 격려하는 톤
"""
```

### 4. 자동 요약 삽입
대화가 길어지면 이전 대화 요약을 시스템 메시지로 삽입:
```python
if total_chars > context_limit and len(messages) > summarize_threshold:
    summary_msg = {"role": "system", "content": "[이전 대화 요약] ..."}
    llm_messages.insert(1, summary_msg)
```

## 변경 파일

- `fastapi/app/core/config.py` (설정값 추가)
- `fastapi/app/api/routes/tutor.py` (_build_llm_messages 개선)
- `fastapi/app/services/tutor_engine.py` (ADELIE_TONE 통합)
