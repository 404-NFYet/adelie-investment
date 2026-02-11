**섹션별 차트 골격 템플릿** (아래 구조를 그대로 따르되, 주석 자리에 실제 데이터를 채우세요):

공통 규칙:
- trace가 1개면 showlegend 생략. trace가 2개 이상이면 "showlegend": true, "legend": {"orientation": "h", "y": -0.25} 추가.
- annotations로 핵심 수치(피크, 최종 수익률 등)를 표기하면 좋음.
- x와 y의 길이는 반드시 동일해야 함.
- 날짜는 "YYYY" 또는 "YYYY-MM" 형식.

### background (시계열 scatter)
```
"chart": {
  "data": [
    {"x": [/* 날짜 5~8개 */], "y": [/* 지표 수치 */], "type": "scatter", "mode": "lines+markers", "name": "/* 지표명 */", "line": {"width": 3}}
  ],
  "layout": {"title": "/* 차트 제목 */", "xaxis": {"title": "기간"}, "yaxis": {"title": "/* 단위 */"}}
}
```

### mirroring (과거 vs 현재 비교 multi-trace scatter)
```
"chart": {
  "data": [
    {"x": [/* 과거 시점 5~6개 */], "y": [/* 과거 수치 */], "type": "scatter", "mode": "lines+markers", "name": "/* 과거 시기명 */", "line": {"width": 2}},
    {"x": [/* 현재 시점 5~6개 */], "y": [/* 현재 수치 */], "type": "scatter", "mode": "lines+markers", "name": "/* 현재 시기명 */", "line": {"width": 2}}
  ],
  "layout": {"title": "/* 차트 제목 */", "xaxis": {"title": "시점"}, "yaxis": {"title": "/* 단위 */"}, "showlegend": true, "legend": {"orientation": "h", "y": -0.25}}
}
```

### difference (시기별 비교 grouped bar)
```
"chart": {
  "data": [
    {"x": [/* 비교 항목 2~3개 */], "y": [/* 과거 수치 */], "type": "bar", "name": "/* 과거 시기 */"},
    {"x": [/* 비교 항목 2~3개 */], "y": [/* 현재 수치 */], "type": "bar", "name": "/* 현재 시기 */"}
  ],
  "layout": {"title": "/* 차트 제목 */", "xaxis": {"title": "항목"}, "yaxis": {"title": "/* 단위 */"}, "barmode": "group", "showlegend": true, "legend": {"orientation": "h", "y": -0.25}}
}
```

### devils_advocate (시나리오 3개 bar + 확률 텍스트)
```
"chart": {
  "data": [
    {"x": [/* 시나리오명 3개 */], "y": [/* 예상 하락률(%) */], "type": "bar", "name": "하락률 (%)", "text": [/* 확률 텍스트 3개 */], "textposition": "outside"}
  ],
  "layout": {"title": "/* 차트 제목 */", "xaxis": {"title": "시나리오"}, "yaxis": {"title": "하락률 (%)"}}
}
```

### simulation (자산가치 라인 + 시나리오 수익률 bar, 2-trace)
```
"chart": {
  "data": [
    {"x": [/* 기간 포인트 4~6개 */], "y": [/* 자산가치(만원) */], "type": "scatter", "mode": "lines+markers", "name": "자산 변화 (만원)", "line": {"width": 3}},
    {"x": ["낙관", "중립", "비관"], "y": [/* 수익률(%) 3개 */], "type": "bar", "name": "수익률 (%)", "text": [/* "+N%", "+N%", "-N%" */], "textposition": "outside"}
  ],
  "layout": {"title": "1,000만원 투자 시뮬레이션 (기간: /* N년/N개월 */)", "xaxis": {"title": "기간 / 시나리오"}, "yaxis": {"title": "가치 (만원) / 수익률 (%)"}, "showlegend": true, "legend": {"orientation": "h", "y": -0.25}}
}
```

### result (시나리오별 수익률 요약 bar)
```
"chart": {
  "data": [
    {"x": ["최적", "평균", "최악"], "y": [/* 수익률(%) 3개 */], "type": "bar", "name": "수익률 (%)", "text": [/* "+N% (N만원)", "+N% (N만원)", "-N% (N만원)" */], "textposition": "outside", "marker": {"color": ["#4CAF50", "#2196F3", "#F44336"]}}
  ],
  "layout": {"title": "시나리오별 수익률 요약 (1,000만원 기준)", "xaxis": {"title": "시나리오"}, "yaxis": {"title": "수익률 (%)"}}
}
```

### action (포트폴리오 비중 또는 진입/청산 포인트)
```
"chart": {
  "data": [
    {"x": [/* 자산/종목명 3~5개 */], "y": [/* 비중(%) */], "type": "bar", "name": "포트폴리오 비중 (%)"}
  ],
  "layout": {"title": "추천 포트폴리오 구성 (%)", "xaxis": {"title": "자산"}, "yaxis": {"title": "비중 (%)"}}
}
```
