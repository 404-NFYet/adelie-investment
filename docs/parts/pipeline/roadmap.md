# Data Pipeline 로드맵

> 파이프라인 개선 과제를 우선순위별로 정리한다.

---

## P0 — 즉시 (이번 스프린트)

### 프롬프트 품질 개선

- [ ] 환각 체크 프롬프트(`hallucination_check.md`, `final_hallucination.md`) 정밀도 향상
  - 현재 환각 체크에서 놓치는 케이스 분석 → 체크리스트 항목 추가
  - 출처 URL 검증 로직 강화 (dead link, 날짜 불일치 등)
- [ ] 역사적 사례 매칭 품질 개선 (`historical_case.md`)
  - 현재 사례가 너무 일반적인 경우가 있음 → 구체적 사례 유도 프롬프트 보강
  - 사례와 현재 상황의 유사도 점수 자체 평가 추가
- [ ] 6페이지 내러티브 섹션 간 연결성 강화
  - 각 섹션이 독립적으로 생성되어 흐름이 끊기는 문제
  - `narrative_body.md`에 이전 섹션 컨텍스트 전달 로직 추가

### 크롤러 안정성

- [ ] 뉴스 크롤러 `news_crawler.py` 타임아웃/재시도 전략 개선
  - Google News RSS 간헐적 차단 대응 (User-Agent 로테이션, 백오프)
  - 크롤링 실패 시 빈 결과 대신 캐시된 이전 결과 활용
- [ ] 리서치 크롤러 `research_crawler.py` PDF 파싱 실패 처리
  - PDF 다운로드 실패, 이미지 기반 PDF 등 예외 케이스 처리
  - MinIO 저장 실패 시 로컬 폴백
- [ ] Attention Scoring `screener.py` pykrx 안정성
  - pykrx API 간헐적 장애 대응 (재시도 + graceful degradation)
  - 공휴일/휴장일 자동 감지 → 직전 영업일 데이터 사용

---

## P1 — 다음 스프린트

### 모델 비용 최적화

- [ ] 프롬프트 토큰 사용량 모니터링 대시보드
  - 각 노드별 input/output 토큰 수 로깅 → LangSmith 대시보드
  - 월간 비용 트렌드 추적
- [ ] Phase 1 요약에서 불필요한 뉴스 필터링 강화
  - 현재 모든 뉴스를 Map 단계에 넣고 있음 → 사전 필터링으로 토큰 절약
  - 중복/유사 뉴스 dedup 로직 추가
- [ ] 모델 다운그레이드 테스트
  - Interface 3 일부 노드(glossary, tone_final)를 gpt-5-mini로 전환 가능 여부 평가
  - 품질 하락 허용 범위 기준 수립

### 모니터링 강화

- [ ] LangSmith 트레이싱 커버리지 100%
  - 현재 일부 노드만 트레이싱 → 모든 LLM 호출에 적용
  - 노드별 성공/실패율, 평균 소요시간 대시보드
- [ ] DB 저장 결과 검증 자동화
  - `save_to_db` 이후 저장된 데이터 무결성 검증 (JSONB 구조, 필수 필드 존재 등)
  - 검증 실패 시 Slack/Discord 알림

---

## P2 — 향후 계획

### 새 데이터 소스 추가

- [ ] DART (전자공시) 연동
  - `DART_API_KEY` 환경변수 이미 config에 정의됨
  - 공시 정보를 curated_context에 추가 → 기업 실적/지배구조 변동 반영
- [ ] 한국은행 경제통계(ECOS) 연동
  - `ECOS_API_KEY` 환경변수 이미 config에 정의됨
  - 거시경제 지표(금리, 환율, GDP 등)를 배경 설명에 활용
- [ ] US 시장 지원 (`--market US`)
  - 현재 KR만 지원 → US 시장 뉴스 크롤러, 종목 스크리너 추가
  - Yahoo Finance API 또는 Alpha Vantage 활용

### 스케줄링 자동화

- [ ] 데일리 파이프라인 자동 실행
  - 현재 수동 실행 → APScheduler 또는 Celery Beat로 자동화
  - 매일 장 마감 후 (KST 16:00) 실행 → 익일 아침 브리핑 준비
- [ ] 실패 시 자동 재시도 + 알림
  - 파이프라인 실패 시 최대 2회 재시도
  - 재시도 실패 시 Discord 알림 + 로그 첨부
- [ ] 멀티 토픽 병렬 실행
  - 현재 순차 실행 (Topic 1 → 2 → 3) → asyncio.gather로 병렬 실행
  - 단, LLM API Rate Limit 고려 필요
