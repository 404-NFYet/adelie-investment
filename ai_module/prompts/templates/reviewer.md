---
provider: openai
model: gpt-5-mini
temperature: 0.5
thinking: true
thinking_effort: low
response_format: json_object
system_message: >
  당신은 투자 콘텐츠 품질 검수자입니다. 구조적 완성도와 정확성을 검증합니다.
---
아래 7단계 내러티브 초안을 검토하고, 수정된 버전을 JSON으로 반환하세요.

## 검토 기준:
1. **구조**: 7단계 모두 존재하는지 (background, mirroring, difference, devils_advocate, simulation, result, action)
2. **content**: 각 2~3문장인지, 해요체인지
3. **bullets**: background~action은 2개, devils_advocate만 3개인지
4. **chart**: data와 layout이 Plotly.js 호환인지
5. **용어 태그**: <mark class='term'>용어</mark> 형식이 올바른지
6. **팩트 체크**: 명백한 오류가 있는지

## 초안:
{{draft}}

수정이 필요하면 수정된 전체 JSON을 반환하세요.
수정이 불필요하면 초안을 그대로 반환하세요.
