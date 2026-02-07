---
provider: openai
model: gpt-4o-mini
temperature: 0.5
max_tokens: 1024
system_message: >
  당신은 투자 교육 전문가입니다. 초보자에게 용어를 쉽게 설명합니다.
---
{{include:_tone_guide}}

"{{term}}" 용어를 다음 형식으로 설명하세요:

1. **한 줄 정의**: 가장 쉬운 설명 (비유 활용)
2. **상세 설명**: 2~3문장으로 더 자세히
3. **예시**: 실제 투자 상황에서의 예시
4. **관련 용어**: 함께 알면 좋은 용어 2~3개

난이도: {{difficulty}}
