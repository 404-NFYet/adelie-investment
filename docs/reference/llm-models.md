# LLM 모델 API 레퍼런스

> 프로젝트에서 사용 중인 LLM 모델 및 프로바이더별 참고 정보를 정리한다.

---

## 1. 프로젝트 내 사용 모델 현황

### 데이터 파이프라인 (`datapipeline/`)

| 용도 | 프로바이더 | 모델 ID | 설정 위치 |
|------|-----------|---------|----------|
| 기본 내러티브 생성 | Anthropic | `claude-sonnet-4-5-20250929` | `config.py` `DEFAULT_MODEL` |
| 차트 코드 생성 | OpenAI | `gpt-5-mini` | `config.py` `CHART_MODEL` |
| 차트 에이전트 | OpenAI | `gpt-5-mini` | `config.py` `CHART_AGENT_MODEL` |
| Phase 1 Map/Reduce 요약 | OpenAI | `gpt-5-mini` | `config.py` `OPENAI_PHASE1_MODEL` |
| Phase 2 Web Search 큐레이션 | OpenAI | `gpt-5.2` | `config.py` `OPENAI_PHASE2_MODEL` |
| 리서치 PDF 요약 | OpenAI | `gpt-5-mini` | `config.py` `OPENAI_RESEARCH_MODEL` |

### 프롬프트 템플릿 (`datapipeline/prompts/templates/`)

| 템플릿 | 프로바이더 | 모델 ID |
|--------|-----------|---------|
| `page_purpose.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `historical_case.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `narrative_body.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `hallucination_check.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `final_hallucination.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `chart_generation.md` | OpenAI | `gpt-5-mini` |
| `glossary_generation.md` | OpenAI | `gpt-5-mini` |
| `3_pages.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `3_theme.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `3_glossary.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `3_chart_generation.md` | OpenAI | `gpt-5-mini` |
| `3_chart_reasoning.md` | OpenAI | `gpt-5-mini` |
| `3_tone_final.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `3_hallcheck_pages.md` | Anthropic | `claude-sonnet-4-5-20250929` |
| `3_hallcheck_chart.md` | OpenAI | `gpt-5-mini` |
| `3_hallcheck_glossary.md` | Anthropic | `claude-sonnet-4-5-20250929` |

### AI 튜터 / 챗봇 (`chatbot/`, `fastapi/`)

| 용도 | 프로바이더 | 모델 ID | 설정 위치 |
|------|-----------|---------|----------|
| 튜터 스트리밍 응답 | OpenAI | `gpt-4o-mini` | `tutor_engine.py` |
| 튜터 에이전트 기본 | OpenAI | `gpt-4o-mini` | `tutor_agent.py` |
| 시각화 생성 (1차) | Anthropic | `claude-3-5-haiku-20241022` | `visualization_tool.py` |
| 시각화 생성 (fallback) | OpenAI | `gpt-4o` | `visualization_tool.py` |
| 사례 검색 | Perplexity | `sonar-pro` | `search_tool.py` |
| 비교 도구 | OpenAI | `gpt-4o-mini` | `comparison_tool.py` |

---

## 2. 프로바이더별 모델 레퍼런스

### 2.1 OpenAI (GPT-5 패밀리 + 레거시)

> **중요**: GPT-5 패밀리는 temperature 기본값이 **1** 이다 (이전 모델은 0.7).
> GPT-5 모델은 `max_tokens` 대신 `max_completion_tokens`를 사용한다.

#### GPT-5 패밀리 (현행)

| 모델 ID | 컨텍스트 윈도우 | 최대 출력 토큰 | 입력 가격 (1M 토큰) | 출력 가격 (1M 토큰) | 비고 |
|---------|---------------|---------------|-------------------|-------------------|------|
| `gpt-5` | 128K | 16,384 | $10.00 | $30.00 | 플래그십 모델, reasoning 지원 |
| `gpt-5-mini` | 128K | 16,384 | $1.50 | $6.00 | 경량 모델, 비용 효율적 |
| `gpt-5.1` | 128K | 32,768 | $12.00 | $36.00 | 강화된 추론 |
| `gpt-5.2` | 256K | 32,768 | $15.00 | $45.00 | 웹 검색 통합, 최신 플래그십 |

- `reasoning_effort`: `low`, `medium`, `high` (thinking 모드 활성화 시)
- GPT-5 이상에서 `temperature` 파라미터를 전달하면 에러가 발생할 수 있음 (기본값 1 사용)

#### 레거시 모델

| 모델 ID | 상태 | 지원 종료 예정 | 비고 |
|---------|------|-------------|------|
| `gpt-4o` | 활성 | 2026-06 (예상) | 멀티모달, 128K 컨텍스트 |
| `gpt-4o-mini` | 활성 | 2026-06 (예상) | 경량 멀티모달 |
| `gpt-4-turbo` | 디프리케이티드 | 2025-06 종료 | `gpt-4o`로 전환 권장 |
| `gpt-4` | 디프리케이티드 | 2025-06 종료 | `gpt-4o`로 전환 권장 |

### 2.2 Anthropic (Claude 4.5 / 4.6)

| 모델 ID | 컨텍스트 윈도우 | 최대 출력 토큰 | 입력 가격 (1M 토큰) | 출력 가격 (1M 토큰) | 비고 |
|---------|---------------|---------------|-------------------|-------------------|------|
| `claude-opus-4-6` | 200K | 32,000 | $15.00 | $75.00 | 최고 성능, 에이전트 코딩 |
| `claude-sonnet-4-5-20250929` | 200K | 16,000 | $3.00 | $15.00 | 성능-비용 균형, 프로젝트 주력 |
| `claude-haiku-4-5-20250929` | 200K | 8,192 | $0.80 | $4.00 | 경량 고속 |
| `claude-3-5-haiku-20241022` | 200K | 8,192 | $0.80 | $4.00 | 레거시 Haiku |
| `claude-3-5-sonnet-20241022` | 200K | 8,192 | $3.00 | $15.00 | 레거시 Sonnet |

- `system` 파라미터를 별도로 전달 (messages 배열이 아닌 최상위 파라미터)
- Extended thinking 지원: `thinking` 파라미터로 제어

#### 레거시 모델

| 모델 ID | 상태 | 지원 종료 예정 |
|---------|------|-------------|
| `claude-3-opus-20240229` | 디프리케이티드 | 2025-03 종료 |
| `claude-3-sonnet-20240229` | 디프리케이티드 | 2025-03 종료 |
| `claude-3-haiku-20240307` | 디프리케이티드 | 2025-03 종료 |

### 2.3 Perplexity (Sonar 패밀리)

| 모델 ID | 컨텍스트 윈도우 | 입력 가격 (1M 토큰) | 출력 가격 (1M 토큰) | 비고 |
|---------|---------------|-------------------|-------------------|------|
| `sonar` | 128K | $1.00 | $1.00 | 기본 검색 모델 |
| `sonar-pro` | 200K | $3.00 | $15.00 | 고급 검색, 복합 질의 지원 |
| `sonar-reasoning` | 128K | $2.00 | $8.00 | 추론 강화 검색 |
| `sonar-reasoning-pro` | 200K | $5.00 | $20.00 | 고급 추론 검색 |

- OpenAI 호환 API (`base_url="https://api.perplexity.ai"`)
- 웹 검색이 자동 통합되어 실시간 정보 반환
- 응답에 `citations` 필드가 포함됨

### 2.4 Google Gemini (2.5 / 3 패밀리)

| 모델 ID | 컨텍스트 윈도우 | 최대 출력 토큰 | 입력 가격 (1M 토큰) | 출력 가격 (1M 토큰) | 비고 |
|---------|---------------|---------------|-------------------|-------------------|------|
| `gemini-2.5-pro` | 1M | 65,536 | $1.25 / $2.50 | $10.00 / $15.00 | 128K 이하/초과로 가격 차등 |
| `gemini-2.5-flash` | 1M | 65,536 | $0.15 / $0.30 | $0.60 / $1.80 | 비용 효율적 경량 모델 |
| `gemini-2.5-flash-lite` | 1M | 65,536 | $0.04 / $0.07 | $0.15 / $0.30 | 초경량, 최저가 |
| `gemini-3.0-pro` | 1M | 65,536 | - | - | 차세대 (출시 예정) |
| `gemini-3.0-flash` | 1M | 65,536 | - | - | 차세대 (출시 예정) |

- `google-genai` 패키지 사용 (`from google import genai`)
- system instruction은 `system_instruction` 파라미터로 별도 전달
- 메시지 role 매핑: OpenAI `assistant` → Gemini `model`
- 1M 토큰 컨텍스트 윈도우로 대용량 문서 처리에 유리

---

## 3. 환경변수

| 환경변수 | 프로바이더 | 설명 |
|---------|-----------|------|
| `OPENAI_API_KEY` | OpenAI | OpenAI API 키 |
| `PERPLEXITY_API_KEY` | Perplexity | Perplexity API 키 |
| `CLAUDE_API_KEY` | Anthropic | Anthropic API 키 |
| `GOOGLE_API_KEY` | Google | Google Gemini API 키 |
| `DEFAULT_MODEL` | - | 기본 내러티브 모델 (기본값: `claude-sonnet-4-20250514`) |
| `CHART_MODEL` | - | 차트 생성 모델 (기본값: `gpt-5-mini`) |
| `GOOGLE_DEFAULT_MODEL` | Google | 기본 Gemini 모델 (기본값: `gemini-2.5-flash`) |

---

## 4. 프로바이더 사용 가이드

### 프롬프트 템플릿에서 프로바이더 지정

```markdown
---
provider: google
model: gemini-2.5-flash
temperature: 0.7
---
프롬프트 본문...
```

지원되는 `provider` 값: `openai`, `perplexity`, `anthropic`, `google`, `gemini`

> `gemini`는 `google`의 별칭이다. 둘 다 Google Gemini API를 호출한다.

### 모델 선택 기준

| 작업 유형 | 권장 모델 | 이유 |
|----------|----------|------|
| 내러티브/분석 (품질 우선) | `claude-sonnet-4-5-*` | 한국어 품질, 긴 출력 |
| 차트/코드 생성 | `gpt-5-mini` | 코드 생성 안정성, 비용 효율 |
| 실시간 검색 | `sonar-pro` | 웹 검색 통합 |
| 대용량 문서 처리 | `gemini-2.5-flash` | 1M 토큰 컨텍스트, 저비용 |
| 빠른 응답 (비용 최적) | `gemini-2.5-flash-lite` | 최저 단가 |
