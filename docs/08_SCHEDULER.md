# 데일리 파이프라인 스케줄러

> 대상 독자: 백엔드 개발자, 배포 담당자
> 매일 오전 8시(KST)에 시장 데이터 수집 → AI 케이스 생성을 자동 실행하는 스케줄러 문서입니다.

---

## 아키텍처

```
FastAPI (lifespan)
  └── APScheduler (AsyncIOScheduler)
        └── CronTrigger: KST 08:00 (= UTC 23:00, 일-목)
              ├── Step 1: seed_fresh_data.py  (pykrx 시장 데이터 수집)
              └── Step 2: generate_cases.py   (OpenAI LLM 역사적 사례 생성)
```

| 구성요소 | 설명 |
|----------|------|
| 라이브러리 | `apscheduler` (APScheduler 3.x) |
| 스케줄러 타입 | `AsyncIOScheduler` — FastAPI 이벤트 루프와 공유 |
| 트리거 | `CronTrigger(hour=23, minute=0, day_of_week="sun,mon,tue,wed,thu")` (UTC) |
| 실행 시간 | KST 월~금 08:00 (UTC 전날 23:00, 일-목) |
| 타임아웃 | 스크립트당 600초 (10분) |
| misfire_grace_time | 3600초 — 서버 재시작 등으로 실행 못 한 경우 1시간 내 보정 |

## 파일 구조

```
backend_api/
├── app/core/scheduler.py          # 스케줄러 코어
├── app/main.py                    # lifespan에서 start/stop 호출
├── scripts/seed_fresh_data.py     # Step 1: 시장 데이터 수집
└── generate_cases.py              # Step 2: AI 케이스 생성
```

## 실행 흐름

### 자동 실행 (프로덕션)

1. FastAPI 서버 시작 시 `lifespan` → `start_scheduler()` 호출
2. `AsyncIOScheduler`가 cron 스케줄 등록
3. 지정 시각(UTC 23:00)에 `run_daily_pipeline()` 트리거
4. `seed_fresh_data.py` 실행 (subprocess) → 성공 시 `generate_cases.py` 실행
5. Step 1 실패 시 Step 2는 실행하지 않고 중단 (에러 로그 기록)
6. 서버 종료 시 `lifespan` → `stop_scheduler()` 호출

### 수동 실행

```bash
# deploy-test 서버에서 직접 실행
docker exec adelie-backend-api python /app/scripts/seed_fresh_data.py
docker exec -e OPENAI_API_KEY="$OPENAI_API_KEY" adelie-backend-api python /app/generate_cases.py
```

## 설정 옵션

`scheduler.py` 내 주요 설정값:

| 설정 | 값 | 설명 |
|------|-----|------|
| `hour` | 23 (UTC) | 실행 시각 (KST 08:00) |
| `day_of_week` | `sun-thu` | UTC 기준 일-목 = KST 월-금 |
| `misfire_grace_time` | 3600 | 1시간 내 지연 실행 허용 |
| `replace_existing` | True | 중복 등록 방지 |
| `timeout` (subprocess) | 600s | 스크립트 실행 제한 시간 |

## 모니터링

### 로그 확인

```bash
# 스케줄러 등록 확인
docker compose -f docker-compose.prod.yml logs backend-api | grep "scheduler"
# 기대 로그: "daily pipeline scheduled for 08:00 KST (UTC 23:00, Sun-Thu)"

# 파이프라인 실행 로그
docker compose -f docker-compose.prod.yml logs backend-api | grep "파이프라인"
# 기대 로그:
#   "=== 데일리 파이프라인 시작 ==="
#   "스크립트 실행 시작: scripts/seed_fresh_data.py"
#   "스크립트 성공: scripts/seed_fresh_data.py"
#   "스크립트 실행 시작: generate_cases.py"
#   "스크립트 성공: generate_cases.py"
#   "=== 데일리 파이프라인 완료 ==="
```

### 에러 발생 시

| 로그 메시지 | 원인 | 조치 |
|------------|------|------|
| `스크립트 없음: ...` | Docker 이미지에 스크립트 미포함 | `docker cp`로 스크립트 복사 |
| `스크립트 타임아웃: ...` | 10분 초과 | pykrx API 또는 OpenAI 응답 지연 확인 |
| `seed_fresh_data 실패 → 파이프라인 중단` | Step 1 실패 | pykrx 연결, DB 상태 확인 |
| `스크립트 실행 오류: ...` | 런타임 에러 | 상세 stderr 로그 확인 |

## 주의사항

- `OPENAI_API_KEY`가 환경변수에 설정되어 있어야 Step 2가 정상 동작합니다.
- 주말(토/일)에는 실행되지 않습니다 (한국 주식시장 휴장).
- 서버가 UTC 23:00~00:00 사이에 재시작되면 `misfire_grace_time` 내에 자동 보정 실행됩니다.
- 스크립트는 `subprocess`로 별도 프로세스에서 실행되므로 FastAPI 이벤트 루프를 블로킹하지 않습니다.
