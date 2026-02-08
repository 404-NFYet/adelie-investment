# AI 파이프라인 가이드

## 아키텍처

### 데이터 생성 파이프라인

#### 1. 시장 데이터 수집 (`scripts/seed_fresh_data.py`)
- pykrx로 당일 급등주, 급락주, 거래량 상위 종목 수집
- `daily_briefings`, `briefing_stocks` 테이블에 저장
- 키워드 title에 `<mark class='term'>용어</mark>` 형식 포함

#### 2. 역사적 사례 생성 (`scripts/generate_cases.py`)
- GPT-4o-mini로 각 키워드별 유사 역사적 사례 자동 생성
- `historical_cases` - 사례 제목, 요약, 전체 스토리, 비교 지표
- `case_matches` - 키워드 ↔ 케이스 매핑 (유사도 점수)
- `case_stock_relations` - 케이스 ↔ 관련 종목 연결

```bash
# deploy-test에서 실행
docker exec -e OPENAI_API_KEY="$KEY" adelie-backend-api python /app/generate_cases.py
```

### 용어 생성 방식: 동적 LLM

정적 DB 용어사전 대신 LLM이 동적으로 용어를 설명합니다.

**용어 마킹 형식**: `<mark class='term'>용어</mark>`

**파이프라인 흐름**:
1. Writer가 `<mark class='term'>용어</mark>` 포함하여 내러티브 생성
2. `extract_terms()` -- 생성된 내러티브에서 용어 추출
3. `generate_glossary()` -- 추출된 용어들의 정의를 LLM으로 일괄 생성
4. `sanitize_marks()` -- 사전에 없는 용어의 마크 태그 제거
5. 최종 데이터에 용어 + 정의를 함께 저장

**챗봇 용어 설명**: 사용자가 질문하면 LLM이 응답 내에서 자연스럽게 괄호 설명 추가.
DB에서 검색 실패 시 LLM이 동적으로 생성하고 Redis에 24시간 캐싱.

## 프롬프트 관리

### 구조
```
ai_module/prompts/
  prompt_loader.py     # 마크다운 프롬프트 로더
  templates/           # 15개 마크다운 템플릿
    _tone_guide.md     # 공용 톤 가이드
    tutor_system.md    # 튜터 시스템 프롬프트
    keyword_extraction.md
    research_context.md
    planner.md
    writer.md          # <mark class='term'> 형식 사용
    reviewer.md
    glossary.md
    ...
```

### 프롬프트 파일 형식
```markdown
---
provider: openai
model: gpt-5-mini
temperature: 0.7
thinking: true
---
{{include:_tone_guide}}
{{variable}} 플레이스홀더
```

### 사용법
```python
from ai_module.prompts import load_prompt
spec = load_prompt("keyword_extraction", count="8", rss_text="...")
```

## 모델 매핑

| 단계 | Provider | 모델 | Thinking |
|------|----------|------|---------|
| Keyword | OpenAI | gpt-5-mini | ON |
| Research | Perplexity | sonar-pro | - |
| Planner | OpenAI | gpt-5-mini | ON |
| Writer | Anthropic | claude-sonnet-4-5 | - |
| Reviewer | OpenAI | gpt-5-mini | ON |
| Tutor | OpenAI | gpt-4o-mini | OFF |
