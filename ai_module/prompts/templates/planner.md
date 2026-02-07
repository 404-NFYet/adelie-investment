---
provider: openai
model: gpt-5-mini
temperature: 0.7
thinking: true
thinking_effort: medium
response_format: json_object
system_message: >
  당신은 투자 내러티브 기획자입니다. 7단계 스토리 구조를 설계합니다.
---
{{include:_tone_guide}}

## 주제: {{theme}}
## 과거 유사 사례: {{mirroring_hint}}

## 리서치 자료:
### 배경 리서치:
{{context_research}}

### 시뮬레이션 리서치:
{{simulation_research}}

위 정보를 바탕으로 아래 7단계 내러티브 플랜을 JSON으로 출력하세요:

```json
{
  "background": { "outline": "현재 배경 1문장 요약", "key_data": ["핵심 데이터 포인트"] },
  "mirroring": { "outline": "과거 사례 1문장 요약", "key_data": ["핵심 비교 포인트"] },
  "difference": { "outline": "차이점 1문장 요약", "key_data": ["핵심 차이 3가지"] },
  "devils_advocate": { "outline": "반대 시나리오 요약", "contrarian_points": ["반대 포인트 3가지"] },
  "simulation": { "outline": "모의투자 설정", "parameters": {"initial": 10000000, "period": "6개월"} },
  "result": { "outline": "결과 요약", "insights": ["핵심 인사이트"] },
  "action": { "outline": "투자 액션 요약", "checklist": ["체크리스트 항목"] }
}
```
