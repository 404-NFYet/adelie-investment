---
provider: openai
model: gpt-5-mini
temperature: 0.7
thinking: true
thinking_effort: medium
response_format: json_object
system_message: >
  당신은 투자 뉴스 분석 전문가입니다. RSS 헤드라인에서 핵심 투자 테마를 추출합니다.
---
아래 RSS 뉴스 헤드라인에서 투자자에게 유의미한 핵심 테마를 {{count}}개 추출하세요.

각 테마는 다음 형식의 JSON 배열로 출력합니다:
```json
[
  {
    "category": "카테고리명 (Macro Economy, Technology, Energy, Policy 등)",
    "domain": "도메인 (macro, technology, energy, policy 등)",
    "keyword": "핵심 키워드 (2~4단어)",
    "title": "매력적인 제목 (15자 이내)",
    "context": "왜 이 테마가 중요한지 2문장 설명",
    "mirroringHint": "유사한 과거 사례 힌트 (예: 2008년 금융위기)"
  }
]
```

{{avoid_section}}

## 뉴스 헤드라인:
{{rss_text}}
