# 데일리 파이프라인 스케줄러

> 대상 독자: 백엔드 개발자, 배포 담당자
> 매일 오후 4시 10분(KST)에 LangGraph 통합 파이프라인을 자동 실행하는 스케줄러 문서입니다.

---

## 아키텍처

```
FastAPI (lifespan)
  └── APScheduler (AsyncIOScheduler)
        └── CronTrigger: KST 16:10 (= UTC 07:10, 월-금)
              └── run_daily_pipeline()
                    ├── LangGraph 파이프라인 (keyword_pipeline_graph.py)
                    ├── Redis 캐시 무효화 (파이프라인 관련 키)
                    └── Materialized View 리프레시 (mv_keyword_frequency)
```

| 구성요소 | 설명 |
|----------|------|
| 라이브러리 | `apscheduler` (APScheduler 3.x) |
| 스케줄러 타입 | `AsyncIOScheduler` — FastAPI 이벤트 루프와 공유 |
| 트리거 | `CronTrigger(hour=7, minute=10, day_of_week="mon,tue,wed,thu,fri")` (UTC) |
| 실행 시간 | KST 월~금 16:10 (UTC 07:10) — 장 마감(15:30) 후 40분 여유 |
| 타임아웃 | 스크립트당 600초 (10분) |
| misfire_grace_time | 3600초 — 서버 재시작 등으로 실행 못 한 경우 1시간 내 보정 |

## 파일 구조

```
fastapi/
├── app/core/scheduler.py          # 스케줄러 코어
└── app/main.py                    # lifespan에서 start/stop 호출

datapipeline/
├── graph.py                       # 18노드 LangGraph StateGraph
├── run.py                         # 파이프라인 실행 진입점
└── scripts/
    ├── seed_fresh_data_integrated.py  # 레거시: 시장 데이터 수집
    └── generate_cases.py              # 레거시: AI 케이스 생성
```

## 실행 흐름

### 자동 실행 (프로덕션)

1. FastAPI 서버 시작 시 `lifespan` → `start_scheduler()` 호출
2. `AsyncIOScheduler`가 cron 스케줄 등록
3. 지정 시각(UTC 07:10, KST 16:10)에 `run_daily_pipeline()` 트리거
4. LangGraph 통합 파이프라인 실행 (`keyword_pipeline_graph.py`)
5. 파이프라인 성공 시 후처리:
   - Redis 캐시 무효화 (파이프라인 관련 키)
   - Materialized View 리프레시 (`mv_keyword_frequency`)
6. 파이프라인 실패 시 중단 (에러 로그 기록)
7. 서버 종료 시 `lifespan` → `stop_scheduler()` 호출

### 수동 실행

```bash
# LangGraph 파이프라인 직접 실행
python -m datapipeline.run --backend live --market KR

# 레거시 스크립트 (deploy-test에서)
docker exec adelie-backend-api python /app/scripts/seed_fresh_data_integrated.py
docker exec adelie-backend-api python /app/scripts/generate_cases.py
```

## 설정 옵션

`scheduler.py` 내 주요 설정값:

| 설정 | 값 | 설명 |
|------|-----|------|
| `hour` | 7 (UTC) | 실행 시각 (KST 16:10) |
| `minute` | 10 | 분 |
| `day_of_week` | `mon-fri` | 월~금 (주식시장 거래일) |
| `misfire_grace_time` | 3600 | 1시간 내 지연 실행 허용 |
| `replace_existing` | True | 중복 등록 방지 |
| `timeout` (subprocess) | 600s | 스크립트 실행 제한 시간 |

## 모니터링

### 로그 확인

```bash
# 스케줄러 등록 확인
docker compose -f docker-compose.prod.yml logs backend-api | grep "scheduler"
# 기대 로그: "daily pipeline scheduled for 16:10 KST (UTC 07:10, Mon-Fri)"

# 파이프라인 실행 로그
docker compose -f docker-compose.prod.yml logs backend-api | grep "파이프라인"
# 기대 로그:
#   "=== 데일리 파이프라인 시작 ==="
#   "LangGraph 파이프라인 실행 시작"
#   "LangGraph 파이프라인 완료"
#   "Redis 캐시 무효화 완료"
#   "MV 리프레시 완료"
#   "=== 데일리 파이프라인 완료 ==="
```

### 에러 발생 시

| 로그 메시지 | 원인 | 조치 |
|------------|------|------|
| `LangGraph 파이프라인 실패 → 파이프라인 중단` | 파이프라인 실행 에러 | 상세 stderr 로그 확인 |
| `스크립트 타임아웃: ...` | 10분 초과 | 크롤링 또는 LLM 응답 지연 확인 |
| `Redis 캐시 무효화 실패` | Redis 연결 문제 | Redis 상태 확인 |
| `MV 리프레시 실패` | DB 연결 문제 | PostgreSQL 상태 확인 |

## 후처리 훅

파이프라인 성공 후 자동 실행되는 후처리:

1. **Redis 캐시 무효화**: 파이프라인 관련 캐시 키 삭제 (새 데이터 즉시 반영)
2. **Materialized View 리프레시**: `mv_keyword_frequency` 뷰 갱신 (키워드 빈도 통계)

## 주의사항

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` 등 LLM API 키가 환경변수에 설정되어 있어야 합니다.
- 주말(토/일)에는 실행되지 않습니다 (한국 주식시장 휴장).
- 실행 시각이 장 마감(15:30) 후 40분인 이유: 당일 종가 데이터 반영을 위한 여유 시간.
- 서버가 UTC 07:00~08:00 사이에 재시작되면 `misfire_grace_time` 내에 자동 보정 실행됩니다.
- 스크립트는 `subprocess`로 별도 프로세스에서 실행되므로 FastAPI 이벤트 루프를 블로킹하지 않습니다.
