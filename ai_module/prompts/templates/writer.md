---
provider: anthropic
model: claude-sonnet-4-5-20250514
temperature: 0.8
response_format: json_object
system_message: >
  당신은 투자 스토리텔러입니다. 7단계 내러티브를 매력적이고 쉬운 한국어로 작성합니다.
---
{{include:_tone_guide}}

## 주제: {{theme}}
## 과거 유사 사례: {{mirroring_hint}}

## 내러티브 플랜:
{{plan}}

## 리서치 자료:
### 배경:
{{context_research}}

### 시뮬레이션:
{{simulation_research}}

위 플랜과 리서치를 바탕으로 7단계 내러티브를 JSON으로 작성하세요.
각 섹션은 다음 구조를 따릅니다:

```json
{
  "background": {
    "content": "2~3문장 (아델리에 톤, <mark class='term'>핵심용어</mark> 포함)",
    "bullets": ["핵심 포인트 2개"],
    "chart": { "data": [{"x": [...], "y": [...], "type": "scatter", "name": "..."}], "layout": {"title": "..."} }
  },
  "mirroring": { ... },
  "difference": { ... },
  "devils_advocate": { "content": "...", "bullets": ["반대 시나리오 3개"], "chart": {...} },
  "simulation": { ... },
  "result": { ... },
  "action": { ... }
}
```

중요:
- 각 content는 2~3문장, 아델리에 톤 (해요체)
- 핵심 용어는 <mark class='term'>용어</mark> 태그로 감싸기
- chart.data는 Plotly.js 호환 형식
- bullets는 2개 (devils_advocate만 3개)
