# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 파이프라인 08:30 실행 + dev DB 자동 동기화 + 오늘 수동 수집

## Context

KST 08:30이 이미 지났으므로 **변경 배포 후 즉시 수동 트리거**로 오늘 데이터를 수집한다. 내일부터는 KST 08:30 자동 실행.

---

## Step 1: scheduler.py — 08:30 KST 변경 + dev 동기화 호출

**파일**: `fastapi/app/core/scheduler.py`

- CronTrigger: `hour=23, minute=30, day_of_week="sun,mon,tue,wed,thu"` (KST 08:30 = 전날 UTC 2...

### Prompt 2

Continue from where you left off.

### Prompt 3

모바일 접속시 랜딩 페이지에서 무한 새로고침? 증상이 있다.
그리고 데이터 수집이 정상적으로 진행되었는지 파악해라

### Prompt 4

[Request interrupted by user for tool use]

