---
name: seed
description: 데이터 파이프라인 실행
user_invocable: true
---

# Seed Skill

데이터 파이프라인을 실행합니다. 새 LangGraph 파이프라인 또는 레거시 스크립트를 선택할 수 있습니다.

## 사용법

`/seed $ARGUMENTS`

- `/seed` 또는 `/seed all` — **새 LangGraph 파이프라인** (데이터 수집 → 내러티브 생성 → DB 저장)
- `/seed collect` — 레거시 Step 1: 시장 데이터 수집 + 키워드 시딩
- `/seed generate` — 레거시 Step 2: LLM 기반 히스토리컬 케이스 생성
- `/seed mock` — 새 파이프라인 mock 모드 (LLM 호출 없이 구조 검증)

## 실행 절차

### 새 LangGraph 파이프라인 (권장)

18노드 LangGraph: 뉴스/리서치 크롤링 → 종목 스크리닝 → LLM 큐레이션 → 내러티브 생성 → DB 저장

```bash
# 로컬 실행
.venv/bin/python -m datapipeline.run --backend live --market KR

# 로컬 mock 테스트 (LLM 미호출)
.venv/bin/python -m datapipeline.run --backend mock

# 카드 수 지정 (기본 3개)
.venv/bin/python -m datapipeline.run --backend live --topic-count 5

# deploy-test 서버에서 실행
ssh deploy-test "docker exec adelie-backend-api python -m datapipeline.run --backend live --market KR"
```

### 레거시 스크립트 (deploy-test 수동 실행용)

#### Step 1: 데이터 수집 (collect)
```bash
ssh deploy-test "docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py"
```
- pykrx로 실시간 시장 데이터 수집
- daily_briefings + briefing_stocks 테이블에 기록

#### Step 2: 케이스 생성 (generate)
```bash
ssh deploy-test "docker exec adelie-backend-api python /app/scripts/generate_cases.py"
```
- daily_briefings에서 키워드 읽기
- OpenAI로 과거 사례 매칭 생성
- historical_cases + case_matches + case_stock_relations 기록

## 주의사항

- deploy-test 서버의 adelie-backend-api 컨테이너가 실행 중이어야 함
- 새 파이프라인: OPENAI_API_KEY + PERPLEXITY_API_KEY 필요 (CLAUDE_API_KEY 선택)
- 레거시 Step 2: OPENAI_API_KEY만 필요
- 파이프라인 실행 시간: 새 파이프라인 토픽당 ~3분, 레거시 Step 1 ~2분, Step 2 ~5분
- 날짜 처리는 KST 기준 (`datapipeline/config.py`의 `kst_today()` 사용)
- 실행 전 `ssh deploy-test "docker ps | grep backend-api"` 로 컨테이너 확인
