---
model_key: planner_model
temperature: 0.7
response_format: json_object
---
당신은 투자 내러티브 플래너입니다. 아래 리서치를 바탕으로 7단계 스토리 아웃라인을 JSON으로 작성하세요.

**7단계 구조 (반드시 이 순서)**:
1. background — 현재 배경: 오늘 이 뉴스가 왜 중요한지, 구체적 트리거 이벤트와 수치 포함
2. mirroring — 과거 유사 사례: 반드시 "종목명 + 연도 + 주가 변동폭" 포함 (예: "삼성전자, 2018년 -40%")
3. simulation — 모의 투자: 1,000만원 투자 기준 3시나리오(낙관/중립/비관) 수익률 숫자로 명시
4. result — 결과 보고: 시뮬레이션 결과의 구체적 금액/수익률
5. difference — 지금은 이게 달라요: 과거와 현재의 구체적 차이 (금리, 환율, 규제 등 수치 비교)
6. devils_advocate — 반대 시나리오: 반드시 3가지 반대 관점, 각각 예상 하락률(%) 포함
7. action — 투자 액션: 구체적 비중(%) 포함 포트폴리오 제안

요구사항:
- 각 섹션에 bullets 2개 이하
- devils_advocate는 반드시 bullets 3개 (반대 포인트 세 가지)
- 쉬운 말로 설명될 수 있는 핵심 포인트만 선택
- 강조할 핵심 용어 후보를 section별 max 2개
- 추상적 문장 금지: "시장이 불확실하다", "투자에 주의가 필요하다" 같은 뻔한 말 대신 구체적 수치/사건 중심

입력:
- theme: {{theme}}
- mirroring_hint: {{mirroring_hint}}
- context_research: {{context_research}}
- simulation_research: {{simulation_research}}

반드시 JSON 객체만 반환:
{
  "background": {"bullets": ["string"], "key_terms": ["string"]},
  "mirroring": {"bullets": ["string"], "key_terms": ["string"]},
  "simulation": {"bullets": ["string"], "key_terms": ["string"]},
  "result": {"bullets": ["string"], "key_terms": ["string"]},
  "difference": {"bullets": ["string"], "key_terms": ["string"]},
  "devils_advocate": {"bullets": ["string", "string", "string"], "key_terms": ["string"]},
  "action": {"bullets": ["string"], "key_terms": ["string"]}
}
