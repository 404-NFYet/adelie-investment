# Backend 로드맵

> Backend(FastAPI) 개선 과제를 우선순위별로 정리한다.

---

## P0 — 즉시 (이번 스프린트)

### DB 쿼리 최적화

- [ ] N+1 쿼리 문제 해결
  - `keywords.py`, `cases.py`에서 관련 데이터 조회 시 lazy loading으로 인한 N+1 발생 가능
  - `selectinload()`, `joinedload()` 적용하여 쿼리 수 최소화
- [ ] JSONB 필드 인덱스 추가
  - `daily_briefings.top_keywords`, `historical_cases.keywords` JSONB 검색 성능 개선
  - GIN 인덱스 추가 migration 생성
- [ ] 포트폴리오 쿼리 최적화
  - 포트폴리오 총 자산 계산 시 모든 거래 내역을 매번 조회 → 캐싱 또는 materialized view 고려
- [ ] 브리핑 목록 페이지네이션
  - `GET /api/v1/briefings` 전체 조회 → offset/limit 또는 커서 기반 페이지네이션

### API 문서화

- [ ] 각 라우트에 docstring + response_model 정의
  - 현재 일부 라우트에 response_model이 없어 Swagger UI에서 응답 구조가 보이지 않음
  - Pydantic v2 스키마를 `response_model`로 명시
- [ ] 에러 응답 표준화
  - 현재 라우트마다 에러 형식이 다름 → `{"status": "error", "detail": "...", "code": "..."}`로 통일
  - `HTTPException` 래퍼 유틸 함수 작성
- [ ] Swagger UI 그룹핑 개선
  - tags 정리 → 도메인별로 그룹핑 (인증, 브리핑, 튜터, 포트폴리오 등)

---

## P1 — 다음 스프린트

### Alembic 워크플로우 개선

- [ ] migration 자동 적용 (Docker 시작 시)
  - 현재 수동으로 `alembic upgrade head` 실행 → Docker entrypoint에서 자동 실행
  - 단, 실패 시 서비스 시작 차단하지 않도록 graceful 처리
- [ ] migration 충돌 방지
  - 여러 팀원이 동시에 migration 생성할 때 head 충돌 발생 가능
  - `alembic merge` 전략 문서화 + CI에서 자동 체크
- [ ] 시드 데이터 관리
  - `database/scripts/`의 초기 데이터 스크립트를 Alembic data migration으로 전환

### 캐싱 전략

- [ ] Redis 캐시 일관성 보장
  - 브리핑/내러티브 데이터 업데이트 시 캐시 무효화 (cache invalidation)
  - 파이프라인 `save_to_db` 이후 관련 캐시 키 삭제 이벤트
- [ ] 캐시 히트율 모니터링
  - Redis INFO 명령으로 hit/miss 비율 추적
  - 캐시 TTL 최적화 (현재 브리핑 6시간 → 트래픽 패턴에 따라 조정)
- [ ] 용어사전 캐시 워밍
  - 자주 조회되는 용어를 서버 시작 시 미리 캐싱

---

## P2 — 향후 계획

### API 버저닝

- [ ] API v2 설계
  - 현재 `/api/v1/` → 향후 `/api/v2/` 경로로 비호환 변경 도입
  - v1과 v2를 동시 운영하는 전환 기간 계획
- [ ] GraphQL 도입 검토
  - 프론트엔드에서 여러 API를 조합하는 패턴이 많음 → GraphQL로 단일 쿼리 가능 여부 평가
  - Strawberry (FastAPI + GraphQL) 프레임워크 검토

### 로깅 및 관찰 가능성

- [ ] 구조화된 로깅 (JSON 형식)
  - 현재 텍스트 로그 → JSON 로그로 전환 (ELK/Loki 연동 대비)
  - 요청 ID, 사용자 ID, 소요 시간 등 메타데이터 포함
- [ ] APM (Application Performance Monitoring)
  - 요청별 레이턴시, DB 쿼리 시간, 외부 API 호출 시간 추적
  - OpenTelemetry 또는 Sentry Performance 도입 검토
- [ ] 감사 로그 (Audit Log)
  - 사용자 로그인, 모의 매매, 설정 변경 등 중요 행동 기록
  - 별도 audit_logs 테이블에 비동기 저장

### 보안 강화

- [ ] JWT 리프레시 토큰 로테이션
  - 현재 리프레시 토큰 재사용 가능 → 사용 시 새 리프레시 토큰 발급 (token rotation)
- [ ] API 키 인증 (서비스 간 통신)
  - 파이프라인 → Backend API 호출 시 JWT 대신 API 키 인증
  - `/api/v1/pipeline/*` 엔드포인트에 API 키 미들웨어 적용
