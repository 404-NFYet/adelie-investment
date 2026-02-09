---
model_key: reviewer_model
temperature: 0.7
response_format: json_object
---
다음 JSON 내러티브를 품질 검수해서 같은 구조로 고쳐주세요.

검수 기준:
- 7개 섹션 모두 존재: background, mirroring, difference, devils_advocate, simulation, result, action
- 모든 섹션에 content/bullets/chart 존재
- content는 2~3문장, 쉬운 표현 유지
- bullets는 최대 2개 (단, devils_advocate는 반드시 3개)
- <mark class="term"> 태그는 핵심 개념 위주로 1~2개 유지
- Plotly chart는 각 섹션마다 유효 구조 유지
- simulation 섹션에 투자 금액, 기간, 수익률 데이터 포함 확인

입력 JSON:
{{draft}}

반드시 JSON 객체만 반환하세요.
