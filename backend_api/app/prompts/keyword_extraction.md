---
model_key: keyword_model
temperature: 0.7
---
다음 RSS 뉴스들을 분석하여 오늘 가장 중요한 투자 테마 후보를 {{count}}개 생성하세요.

**선정 기준 (Diversity & Relevance)**:
오늘의 뉴스를 가장 잘 설명하는 핵심 테마들을 선정하세요.
특정 카테고리에 얽매일 필요는 없으나, 상호 겹치지 않는 다양한 관점으로 구성해야 합니다.
중요: 생성한 테마의 Keyword는 서로 완전히 달라야 하며, 같은 도메인 반복을 피하세요.
중요: 미국 증시/기술주 과열처럼 한 클러스터로 묶이는 유사 테마를 중복 생성하지 마세요.

도메인(domain) 후보 예시:
- equities, fixed_income, fx, commodities, crypto, geopolitics, policy, supply_chain, consumer, healthcare, energy, technology

{{avoid_section}}

각 주제 JSON 배열 필드:
- category, domain, keyword, title, context, mirroringHint

RSS Text:
{{rss_text}}
