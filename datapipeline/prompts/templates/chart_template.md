---
model_key: story_model
temperature: 0.3
response_format: json_object
---
차트 JSON 템플릿 및 예시

이 파일은 작성기(`writer.md`)가 항상 일관된 Plotly 차트 JSON을 생성하도록 예시와 템플릿을 제공합니다.
프롬프트에서 아래 형태의 `chart` 객체를 각 섹션에 포함해 달라고 명확히 요구하세요.

요구 형식 (항상 JSON 객체):

```json
{
  "data": [
    {
      "x": [...],        // 문자열 날짜 또는 카테고리 목록
      "y": [...],        // 숫자 값 목록 (x와 길이 동일)
      "type": "scatter", // 또는 "bar"
      "name": "Trace 이름"
    }
  ],
  "layout": {
    "title": "차트 제목",
    "xaxis": {"title": "X축 라벨"},
    "yaxis": {"title": "Y축 라벨"},
    "annotations": []   // 선택적: 주요 포인트 주석
  }
}
```

최소 체크리스트 (작성기 프롬프트에 반드시 포함):
- `data`는 리스트여야 함. 첫 번째 trace는 `x`와 `y`를 모두 가져야 함. 길이는 같아야 함.
- `type`은 `scatter`(라인) 또는 `bar`(막대) 권장.
- `layout.title`이 반드시 존재해야 함.

예시 1 — 간단한 시계열 차트 (배경/미러링용)

```json
{
  "data": [
    {
      "x": ["2020", "2021", "2022", "2023", "2024"],
      "y": [100, 110, 105, 120, 130],
      "type": "scatter",
      "name": "지수 추이"
    }
  ],
  "layout": {
    "title": "지수 연도별 추이",
    "xaxis": {"title": "연도"},
    "yaxis": {"title": "지수 (포인트)"}
  }
}
```

예시 2 — 모의 투자 시뮬레이션 (simulation 섹션 권장)

```json
{
  "data": [
    {
      "x": ["T0", "T1", "T2", "T3", "T4"],
      "y": [10000000, 10500000, 9800000, 11200000, 12500000],
      "type": "scatter",
      "name": "모의 투자(원)"
    },
    {
      "x": ["T0", "T1", "T2", "T3", "T4"],
      "y": [100, 102, 98, 110, 125],
      "type": "scatter",
      "name": "상대 지수(%)"
    }
  ],
  "layout": {
    "title": "1000만 원 모의 투자 결과 (기간별 자산가치)",
    "xaxis": {"title": "기간"},
    "yaxis": {"title": "자산 가치 (원)"},
    "annotations": [
      {"x": "T4", "y": 12500000, "text": "최종: +25%", "showarrow": true}
    ]
  },
  "meta": {
    "initial_capital": 10000000,
    "holding_period": "1 year",
    "final_return_pct": 25
  }
}
```

참고:
- `meta` 필드는 프론트엔드에서 표시할 추가 메타(원금, 기간, 수익률 등)를 넣을 때 유용합니다. Plotly는 `meta`를 자동으로 사용하지 않으므로 프론트엔드에서 `chart.meta`를 읽어 별도 UI로 표시하세요.
- 작성기에게는 `chart` 외에 `chart.data`의 단위(원/%, 날짜 형식)를 명시하도록 요구하면 파싱 오류를 줄일 수 있습니다.

