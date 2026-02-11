---
name: seed
description: 데이터 파이프라인 실행
user_invocable: true
---

# Seed Skill

deploy-test 서버의 데이터 파이프라인을 실행합니다.

## 사용법

`/seed $ARGUMENTS`

- `/seed` 또는 `/seed all` — 전체 파이프라인 (수집 → 생성)
- `/seed collect` — Step 1만: 시장 데이터 수집 + 키워드 시딩
- `/seed generate` — Step 2만: LLM 기반 히스토리컬 케이스 생성

## 실행 절차

### Step 1: 데이터 수집 (collect)
```bash
ssh deploy-test "docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py"
```
- pykrx로 실시간 시장 데이터 수집
- daily_briefings + briefing_stocks 테이블에 기록

### Step 2: 케이스 생성 (generate)
```bash
ssh deploy-test "docker exec adelie-backend-api python /app/scripts/generate_cases.py"
```
- daily_briefings에서 키워드 읽기
- OpenAI gpt-4o-mini로 과거 사례 매칭 생성
- historical_cases + case_matches + case_stock_relations 기록

## 주의사항

- deploy-test 서버의 adelie-backend-api 컨테이너가 실행 중이어야 함
- Step 2는 OPENAI_API_KEY가 .env에 설정되어 있어야 함
- 파이프라인 실행 시간: Step 1 ~2분, Step 2 ~5분
- 실행 전 `ssh deploy-test "docker ps | grep backend-api"` 로 컨테이너 확인
