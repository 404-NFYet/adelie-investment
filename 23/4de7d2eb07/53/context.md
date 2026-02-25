# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# 데이터 파이프라인 스케줄러 수정 계획

## Context

deploy-test에서 스케줄러가 2026-02-25(화)를 "휴장일"로 오판 → 모닝(09:00 KST) + 데일리(16:10 KST) 파이프라인 모두 스킵.

### 근본 원인 2가지

**1. pykrx 타이밍 + lru_cache 영구 캐시**
- 09:00 KST(장 시작 직후): 당일 OHLCV 미확정 → pykrx가 전일 반환 → `nearest ≠ today` → False
- `@lru_cache`가 False를 **영구 캐시** → 16:10 KS...

### Prompt 2

진행해라

