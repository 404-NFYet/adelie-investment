# 정지훈 (J2hoon10) — 프로젝트 변경이력

> 역할: AI/챗봇 개발
> 기간: 2026-01-20 ~ 현재 (개발 진행 중)
> 기술 스택: LangGraph, LangChain, OpenAI, Perplexity, Claude, FastAPI, SSE, Redis, Neo4j

---

## Phase 1: 프로젝트 초기화 및 AI 모듈 기반 구축 (01-29 ~ 02-03)

### Situation
프로젝트 시작 시점에 백엔드 API 서버, AI 모듈, 데이터 파이프라인 등 핵심 인프라가 전무한 상태였다. AI 기반 금융 교육 플랫폼의 핵심 기능인 LLM 연동과 챗봇 튜터를 처음부터 설계하고 구현해야 했으며, 동시에 다른 팀원들이 즉시 개발에 착수할 수 있도록 백엔드 뼈대와 데이터 수집 기반을 빠르게 구축해야 했다.

### Task
- FastAPI 백엔드 애플리케이션 구조 설계 및 초기화
- LangChain + OpenAI + Perplexity 기반 AI 모듈 초기화
- 데이터 파이프라인 초기 구조 설계
- LangGraph 기반 AI 튜터 에이전트 프로토타입 구현
- 공급망 분석용 Neo4j 연동 스크립트 개발

### Action
FastAPI 앱 구조를 설계하고 라우터 동적 등록 방식을 도입하여, 각 모듈이 독립적으로 라우트를 추가할 수 있는 확장 가능한 구조를 확립하였다. SQLAlchemy 비동기 모델 17종(briefing, company, glossary, historical_case, learning, portfolio, report, tutor, user 등)과 Pydantic v2 응답 스키마를 정의하여 데이터 레이어의 기반을 완성하였다. 튜터, 브리핑, 용어집 등 7개 주요 API 엔드포인트를 구현하고, hybrid_rag 서비스와 Redis 캐시 레이어를 포함한 서비스 계층을 구축하였다(+2,237라인).

AI 모듈은 LangChain + OpenAI + Perplexity를 통합하여 초기화하였고, LangGraph 기반 튜터 에이전트(`tutor_agent.py`)와 Redis 체크포인터(`checkpointer.py`)를 구현하여 대화 상태를 유지하는 멀티턴 챗봇의 프로토타입을 완성하였다(+495라인). 에이전트 프롬프트 시스템(`prompts.py`, 165라인)을 설계하여 수준별 튜터 응답 전략을 차별화하였다.

데이터 파이프라인 초기 구조를 설계하고 Neo4j 공급망 그래프 스크립트 3종(정규화, 배치 적재, OpenDART 추출)을 작성하여 총 +1,127라인의 그래프 데이터 기반을 마련하였다.

### Result
- 커밋 8건, 코드 변경량 약 +8,800라인
- FastAPI 백엔드 구조 확립: 모델 17종, 스키마 7종, 라우트 7개, 서비스 7개
- LangGraph 튜터 에이전트 프로토타입 동작 확인 (상태 관리 + 프롬프트 분기)
- Neo4j 공급망 그래프 적재 자동화 완성
- 전 팀원이 즉시 병렬 개발에 착수할 수 있는 백엔드/AI 기반 마련

---

## Phase 2: 서비스 확장 — API·시각화·매매·파이프라인 (02-04 ~ 02-07)

### Situation
Phase 1에서 확립한 기본 구조 위에 실제 서비스 기능들을 본격 구현해야 했다. 내러티브 콘텐츠 열람, 포트폴리오 관리, 자유매매, 차트 시각화 등 사용자 대면 기능이 아직 없었으며, LLM 프로바이더별로 코드가 분산되어 통합 관리가 어려운 상태였다. 또한 매일 자동으로 데이터를 수집하고 콘텐츠를 생성하는 스케줄러와, 사용자 간 경쟁을 유도하는 리더보드 기능이 요구되었다.

### Task
- 내러티브·포트폴리오·튜터·시각화 관련 전체 서비스 및 API 구현
- MultiProviderClient 설계로 OpenAI/Perplexity/Claude 통합
- 마크다운 기반 프롬프트 관리 시스템 구축
- KIS API 연동 자유매매 + 피드백 API 개발
- 리더보드 API + 데일리 파이프라인 스케줄러 추가
- LLM 기반 historical_cases 자동 생성 스크립트 작성

### Action
내러티브·포트폴리오·튜터 서비스 계층을 구현하였다. `narrative_builder.py`, `portfolio_service.py`, `tutor_engine.py`, `stock_resolver.py`, `stock_price_service.py`, `code_executor.py`, `chart_storage.py` 등 7개 서비스(+1,252라인)와 5개 API 라우트(+681라인), 스키마 2종(+174라인), 모델 2종(+68라인)을 완성하여 사용자 대면 기능의 백엔드를 전면 구축하였다.

AI 통합을 위해 `MultiProviderClient`(220라인)를 설계하여 OpenAI, Perplexity, Claude 3개 프로바이더를 단일 인터페이스로 추상화하였다. 프롬프트 관리 시스템에서는 `prompt_loader.py`(199라인)와 마크다운 템플릿 12종을 작성하여, frontmatter 메타데이터(provider, model, temperature, thinking)로 프롬프트별 LLM 설정을 선언적으로 관리할 수 있게 하였다(총 +1,212라인).

KIS(한국투자증권) API를 연동한 자유매매 서비스(`trading.py` 195라인, `kis_service.py` 245라인)와 피드백 API(212라인)를 구현하여 실시간 주식 거래 시뮬레이션 기능을 완성하였다(+678라인). 재무 데이터 수집기(`financial_collector.py` 190라인)와 DB 리셋 스크립트(219라인)를 추가하여 데이터 파이프라인을 보강하였다.

리더보드 API와 APScheduler 기반 데일리 스케줄러를 추가하고, LLM을 활용한 historical_cases 자동 생성 스크립트(232라인)를 작성하여 과거 투자 사례 데이터의 자동 확보 체계를 구축하였다. 차트 시각화 도구(`visualization_tool.py` 117라인)와 Claude 서비스 연동도 완성하였다.

### Result
- 커밋 14건, 코드 변경량 약 +5,700라인
- 서비스 기능 전면 구현: 내러티브, 포트폴리오, 튜터, 시각화, 자유매매
- MultiProviderClient + 프롬프트 관리 시스템으로 LLM 3종 통합 운영 체계 확립
- 마크다운 프롬프트 템플릿 12종으로 AI QA 담당자의 독립적 프롬프트 수정 워크플로우 확립
- 데일리 스케줄러로 매일 자동 데이터 수집·콘텐츠 생성 자동화

---

## Phase 3: 구조 리팩토링 — 모듈 분리·캐싱·레거시 정리 (02-12)

### Situation
Phase 2에서 빠르게 기능을 확장한 결과, 챗봇과 데이터 파이프라인 간 AI 설정 코드가 중복되고, 레거시 AI 서비스 코드(openai_service.py 243라인, perplexity_service.py 252라인, diversity.py 125라인 등)가 MultiProviderClient 도입 이후에도 잔존하고 있었다. 또한 API 응답 캐싱이 부재하여 반복 요청에 대한 성능 개선이 필요했고, 학습진도 추적과 리포트 생성 API가 아직 구현되지 않은 상태였다.

### Task
- chatbot/datapipeline 간 공통 AI 설정 모듈 추출
- chatbot 전용 prompt_loader 독립 구현
- 레거시 AI 서비스 코드 정리 및 6페이지 내러티브 구조 전환
- Redis 캐싱 도입 + 학습진도/리포트 API 구현
- 파이프라인 후처리 자동화 (캐시 무효화 + MV 리프레시)
- generate_cases의 MultiProviderClient 연동

### Action
`shared/` 모듈을 추출하여 `ai_config.py`(89라인)와 `langsmith_config.py`(170라인)를 공통화하였다. 이를 통해 chatbot과 datapipeline 양쪽에서 중복되던 AI 설정 코드 약 500라인을 제거하였다(+306 / -496). chatbot 전용 `prompt_loader.py`를 173라인으로 독립 구현하여 마크다운 템플릿의 동적 로딩과 frontmatter 파싱을 챗봇 맥락에 최적화하였다.

데이터 파이프라인에서 레거시 AI 서비스 코드(claude_service.py, openai_service.py, perplexity_service.py, diversity.py)를 전면 삭제하고(-665라인), ai_service를 6페이지 내러티브 생성 구조(page_purpose → historical_case → narrative_body → hallucination_check → chart_generation → glossary_generation)로 전환하였다. generate_cases 스크립트에 MultiProviderClient를 연동하여 다중 프로바이더 폴백을 적용하였다.

Redis 기반 API 캐싱을 도입하고(`redis_cache.py` 38라인), 학습진도 API(244라인)와 리포트 API(188라인)를 신규 구현하였다. 불필요한 레거시 라우트(chat.py, tutor_explain.py)를 삭제하고 라우트 구조를 정리하였다(+552 / -151). 파이프라인 실행 완료 후 Redis 캐시 무효화와 PostgreSQL Materialized View 리프레시를 자동 수행하는 후처리 로직을 구현하였다(+83라인).

### Result
- 커밋 7건, 코드 변경량 약 +1,200라인 (순감소 포함 시 레거시 -1,300라인 정리)
- AI 설정 중복 제거: 2개 모듈 → 1개 shared/ 모듈로 통합
- 레거시 AI 서비스 4개 파일 완전 삭제, 6페이지 내러티브 구조 확립
- Redis 캐싱 도입으로 반복 API 호출 응답시간 단축
- 파이프라인 후처리 자동화로 데이터 최신성 즉시 반영 보장

---

## Phase 4: 챗봇 서비스 복원 및 안정화 (02-16)

### Situation
Phase 3의 대규모 리팩토링 과정에서 챗봇 서비스의 일부 기능이 비활성화되었고, glossary 도구가 동기 호출로 인해 이벤트 루프를 블로킹하는 문제가 발생하였다. 세션 관리 API의 안정성이 부족하고, 프롬프트 체계가 정리되지 않은 상태에서 프론트엔드 AI 튜터 기능의 사용자 경험이 저하되고 있었다. 또한 SSE 스트리밍 중 LLM 호출 실패 시 무한 대기가 발생하는 문제가 보고되었다.

### Task
- 챗봇 세션 관리 API 안정화 (생성, 조회, 삭제)
- glossary 도구의 비동기 전환
- 에러 재시도 로직 구현 (LLM 호출 실패 대응)
- 프롬프트 체계 정리 및 불필요한 코드 제거
- 프론트엔드 TutorContext 세션 관리 개선

### Action
챗봇 서비스 전반을 복원하고 안정화하는 작업을 수행하였다. `tutor_sessions.py` 라우트에 세션 생성·조회·삭제 로직을 보강하고, `tutor_engine.py`를 99라인 이상 개선하여 SSE 스트리밍의 안정성을 확보하였다. `glossary_tool.py`를 비동기로 전면 전환하여(+159 / -기존 동기 코드) 이벤트 루프 블로킹을 해소하였다.

에이전트 프롬프트(`prompts.py`)를 대폭 정리하여 198라인에서 불필요한 중복을 제거하고, 튜터 시스템 프롬프트(`tutor_system.md`)를 재정비하였다. LLM 호출 실패에 대비한 exponential backoff 기반 재시도 로직(최대 3회)을 도입하여, 일시적 API 장애 시에도 서비스가 중단되지 않도록 하였다.

프론트엔드에서는 `TutorContext.jsx`(+131라인)의 세션 관리 로직을 개선하여 세션 생성·복구·정리 흐름을 안정화하고, `TutorPanel.jsx`와 `MessageBubble.jsx`의 UI를 SSE 스트리밍에 최적화하였다. 테스트 코드(`test_ai_tools.py`)도 함께 업데이트하였다.

### Result
- 커밋 1건(대규모 통합 커밋), 10개 파일 변경, +424 / -350라인
- glossary 도구 비동기 전환으로 이벤트 루프 블로킹 해소
- exponential backoff 재시도 로직으로 LLM 호출 실패 시 자동 복구 (최대 3회)
- 세션 API 안정화로 AI 튜터 기능의 사용자 경험 정상화
- 프론트엔드 TutorContext 세션 관리 개선으로 챗봇 진입·퇴장 플로우 안정화

---

## 전체 요약

| 지표 | 수치 |
|------|------|
| 총 커밋 수 | 33건 (머지 커밋 포함) |
| 코드 변경량 | 약 +16,000 / -2,000라인 |
| 활동 기간 | 01-29 ~ 02-16 (19일) |
| 구현 API 엔드포인트 | 15개 이상 (튜터, 브리핑, 용어집, 내러티브, 포트폴리오, 시각화, 매매, 피드백, 학습, 리포트, 리더보드, 파이프라인 등) |
| SQLAlchemy 모델 | 17종 |
| 서비스 모듈 | 12개 이상 |
| LLM 프로바이더 통합 | 3종 (OpenAI, Perplexity, Claude) |
| 프롬프트 템플릿 | 12종 이상 (.md) |
| 챗봇 도구 | 5종 (검색, 브리핑, 비교, 시각화, 용어집) |

프로젝트 초기화부터 AI 튜터 챗봇, 멀티 LLM 프로바이더 통합, 서비스 전면 구현, 구조 리팩토링, 최종 안정화까지 AI/백엔드 전 영역의 핵심 아키텍처를 주도적으로 설계하고 구현하였다.
