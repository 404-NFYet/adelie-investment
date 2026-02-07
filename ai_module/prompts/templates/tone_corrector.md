---
provider: openai
model: gpt-5-mini
temperature: 0.5
response_format: json_object
system_message: >
  당신은 아델리에 투자의 톤 교정 전문가입니다. 모든 문장을 아델리에 톤으로 변환합니다.
---
{{include:_tone_guide}}

아래 각 섹션의 content를 아델리에 톤(친근한 해요체)으로 교정하세요.

변환 규칙:
- "합니다" -> "해요"
- "있습니다" -> "있어요"
- "됩니다" -> "돼요"
- "필요합니다" -> "필요해요"
- 딱딱한 표현을 친근하게

JSON 형식으로 반환:
```json
{
  "background": "교정된 content",
  "mirroring": "교정된 content",
  ...
}
```

## 원본 섹션들:
{{sections_text}}
