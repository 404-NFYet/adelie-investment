# 허진서 (jjjh02) — 프로젝트 변경이력

> 역할: 백엔드 개발
> 기간: 2026-01-20 ~ 현재 (개발 진행 중)
> 기술 스택: FastAPI, SQLAlchemy, PostgreSQL, JWT, Prometheus, Alembic

---

## 정량 요약

| 지표 | 수치 |
|------|------|
| 총 커밋 수 | 38개 |
| 코드 변경량 | +4,060 / -2,030 라인 |
| 활동일 수 | 7일 (02-04, 02-05, 02-07, 02-12, 02-13, 02-14, 02-16) |
| 영향 파일 수 | ~130개 파일 (Spring Boot 전체 제거 포함) |
| Alembic 마이그레이션 작성 | 7건 |
| API 라우트 신규/리팩토링 | 15+ 엔드포인트 |

---

## Phase 1: 프로젝트 초기 구축 (02-04 ~ 02-07)

### Situation

프로젝트 초기에는 사용자 인증 시스템이 전혀 존재하지 않았다. 플랫폼의 핵심 기능인 포트폴리오 관리, 학습 진도 추적, 모의투자 등은 모두 사용자 식별을 전제로 하므로, 회원 관리와 보안 인증 체계를 처음부터 설계하고 구축해야 하는 상황이었다. 동시에 AI 튜터가 활용할 종목 비교 도구와 용어 하이라이팅 서비스, 그리고 금융 데이터를 그래프 구조로 적재할 시스템도 필요하였다.

### Task

- JWT 기반 회원 인증/인가 시스템을 설계하고, Spring Boot 기반 인증 서버를 구축한다.
- Neo4j 그래프 데이터베이스에 OpenDART 공시 데이터를 배치 적재하는 자동화 파이프라인을 만든다.
- AI 튜터 챗봇이 사용할 종목 비교 도구(LangChain Tool)와 용어 하이라이팅 서비스를 구현한다.

### Action

**Spring Security + JWT 인증 서버 구축**: Spring Boot 기반으로 인증 전용 백엔드를 구현하였다. BCrypt 암호화를 적용한 회원가입/로그인 API, JwtAuthenticationFilter를 통한 토큰 검증 체인, 환경변수 기반 CORS 동적 설정을 포함하여 총 18개 파일, 1,146라인 규모의 인증 서버를 완성하였다. 이후 운영 환경에서 CORS 허용 도메인을 유연하게 관리할 수 있도록 SecurityConfig의 환경변수 동적 설정도 추가하였다.

**Neo4j 배치 적재 자동화**: 금융감독원 OpenDART API에서 기업 공시 데이터를 추출하고, LLM을 활용하여 구조화한 뒤 Neo4j 그래프 DB에 적재하는 5개의 스크립트(780라인)를 작성하였다. 종목 간 업종, 테마, 공급망 관계를 그래프로 모델링하여 종목 비교 및 관련 종목 탐색의 기반을 마련하였다.

**AI 챗봇 도구 개발**: 두 종목의 재무 지표와 주가 추이를 비교 분석하는 `comparison_tool.py`(104라인)와, 내러티브 텍스트 내 금융 전문 용어를 사전 기반으로 자동 감지하여 하이라이팅하는 `term_highlighter.py`(142라인)를 구현하였다.

### Result

- 프로젝트에 최초의 인증 체계가 도입되어, 이후 모든 사용자 식별 기반 기능(포트폴리오, 학습, 알림 등)의 개발이 가능해졌다.
- Neo4j 그래프 DB에 종목 관계 데이터가 적재되어, 종목 간 연관성 분석이라는 교육 콘텐츠 확장의 기반이 구축되었다.
- 종목 비교 도구와 용어 하이라이팅 서비스가 AI 튜터에 통합되어 초보 투자자를 위한 교육적 기능이 강화되었다.

---

## Phase 2: 핵심 기능 구현 (02-12)

### Situation

Phase 1에서 Spring Boot로 구축한 인증 서버와 FastAPI 백엔드가 이중으로 운영되면서 문제가 드러났다. 두 서비스 간 JWT 서명 알고리즘이 불일치(Spring: HS384, FastAPI: HS256)하여 토큰 검증이 실패하는 보안 이슈가 발생하였다. 또한 서비스 두 개를 각각 빌드/배포/모니터링해야 하므로 인프라 비용과 유지보수 복잡도가 불필요하게 높았다. Alembic 마이그레이션도 개발 환경에서 불안정하여 팀원들이 스키마 불일치로 인한 오류를 자주 겪고 있었다.

### Task

- Spring Boot 인증 로직을 FastAPI로 완전히 마이그레이션하고, Spring Boot 서비스를 제거한다.
- JWT 서명 알고리즘 불일치를 해결하여 프론트엔드-백엔드 간 토큰 검증을 안정화한다.
- Alembic 마이그레이션 워크플로우를 안정화하고, Docker Compose에 db-migrate 서비스를 추가한다.
- 검색 성능을 위한 pg_trgm GIN 인덱스, pgvector 확장, 키워드 빈도 Materialized View를 구축한다.

### Action

**Spring Boot → FastAPI 인증 통합**: Spring Boot의 인증 로직(AuthService, JwtService, SecurityConfig 등)을 Python PyJWT 기반으로 재구현하였다. `auth_service.py`(206라인)에 회원가입, 로그인, 토큰 리프레시, 사용자 CRUD를 구현하고, `auth.py` 스키마와 라우트를 새로 작성하였다. 이 과정에서 Spring Boot 코드 1,335라인을 삭제하고 FastAPI 코드 325라인으로 대체하여, 코드량 75% 감소와 함께 백엔드 아키텍처를 단일 서비스로 통합하였다.

**JWT 알고리즘 통일**: Spring Boot에서 HS384로 서명하고 FastAPI에서 HS256으로 검증하던 불일치를 발견하고, 양쪽을 HS256으로 통일하였다. 마이그레이션 기간 동안 기존 HS384 토큰도 검증 가능하도록 `auth.py`에 fallback 로직을 추가하였다.

**마이그레이션 안정화**: Docker Compose에 `db-migrate` 서비스를 추가하여 컨테이너 기반 마이그레이션 실행을 표준화하였다. Alembic 인덱스 마이그레이션에 방어적 처리(IF EXISTS/IF NOT EXISTS)를 적용하고, 분기된 마이그레이션 헤드를 머지하여 개발 환경의 스키마 일관성을 확보하였다.

**DB 최적화 마이그레이션**: pg_trgm GIN 인덱스(텍스트 유사도 검색), pgvector 확장(임베딩 벡터 저장), 키워드 빈도 Materialized View를 구축하는 163라인 규모의 마이그레이션을 작성하여 검색 성능의 기반을 마련하였다.

### Result

- 백엔드가 FastAPI 단일 서비스로 통합되어 배포 파이프라인이 2개에서 1개로 단순화되고, 서비스 간 통신 오버헤드가 완전히 제거되었다.
- JWT 알고리즘 통일로 토큰 검증 실패율이 0%로 안정화되었다.
- db-migrate 서비스 도입으로 팀 전체의 마이그레이션 실행이 `docker compose run db-migrate` 한 줄로 표준화되어, 스키마 불일치 이슈가 해소되었다.
- pg_trgm 인덱스 적용으로 한글 텍스트 LIKE 검색 응답시간이 개선될 기반이 마련되었다.

---

## Phase 3: 통합 및 최적화 (02-13 ~ 02-14)

### Situation

Phase 2에서 인증 시스템과 DB 기반을 정비한 후, 프론트엔드와 데이터 파이프라인이 본격적으로 연동되면서 새로운 문제들이 드러났다. 포트폴리오 API에서 사용자별 보유 종목을 조회할 때 N+1 쿼리가 발생하여 종목 10개 기준 DB 쿼리가 11회 실행되고 있었다. 키워드 API도 동일한 N+1 패턴이 있었다. 또한 API 엔드포인트마다 `user_id`를 URL path parameter로 받고 있어 다른 사용자의 데이터에 접근할 수 있는 보안 취약점이 존재하였다. 모의투자 기능은 한국 주식시장 휴장일에도 거래가 가능한 상태였으며, DB/Redis 커넥션 풀 크기가 기본값(5)으로 설정되어 동시 접속 시 커넥션 고갈이 우려되었다. Prometheus 기반 모니터링도 아직 연동되지 않아 운영 중 성능 이슈를 사전에 감지할 수 없었다.

### Task

- N+1 쿼리를 배치 조인으로 변환하여 DB 호출 횟수를 최소화한다.
- 모든 API에서 user_id path parameter를 JWT에서 추출하는 방식으로 전환하여 보안을 강화한다.
- 모의투자에 휴장일 거래 차단 로직을 적용하고, DB 스키마를 정비한다.
- Prometheus 메트릭 엔드포인트를 추가하고, 시스템 모니터링 기반을 구축한다.
- datetime naive/aware 불일치, KST 날짜 기준 등 데이터 정합성 이슈를 해결한다.

### Action

**N+1 쿼리 최적화**: 포트폴리오 API의 보유 종목 조회에서 `selectinload`를 활용한 배치 조인으로 전환하여, 종목 N개 조회 시 발생하던 N+1회 쿼리를 2회(메인 쿼리 + 관계 조인)로 감소시켰다. 키워드 API도 동일한 패턴을 적용하였다. DB 커넥션 풀을 기본값 5에서 20으로, Redis 커넥션 풀도 10에서 30으로 증가시켜 동시 접속 대응력을 강화하였다.

**JWT 기반 인증 전면 전환**: portfolio, learning, notification, tutor 등 13개 파일에 걸쳐 `user_id` path parameter를 `Depends(get_current_user)`로 교체하였다. 프론트엔드의 API 호출 코드도 동시에 수정하여 URL에서 user_id를 제거하고, Authorization 헤더에서 JWT를 통해 사용자를 식별하도록 전환하였다. tutor API는 optional auth로 설정하여 미인증 사용자도 기본 기능을 이용할 수 있게 하였다.

**모의투자 DB 정비 및 휴장일 차단**: 한국 주식시장의 공휴일/임시휴장을 판별하는 `market_calendar.py`(39라인)를 구현하고, 파이프라인 스케줄러에 휴장일 스킵 로직을 추가하였다. 모의투자 테이블의 Alembic 마이그레이션(96라인)을 작성하여 스키마를 정비하고, 거래 API에 휴장일 체크를 적용하였다.

**Prometheus 메트릭 및 모니터링**: FastAPI에 `prometheus-fastapi-instrumentator`를 통합하여 `/metrics` 엔드포인트를 추가하였다. 요청 수, 응답 시간, 에러율 등의 메트릭이 자동 수집되어 Grafana 대시보드에서 실시간 모니터링이 가능해졌다.

**datetime 정합성 해결**: 보상(reward) 서비스에서 naive datetime과 aware datetime이 혼재되어 비교 연산 시 TypeError가 발생하던 문제를 `utcnow()`로 통일하여 해결하였다. keywords/today API의 날짜 기준을 UTC에서 KST로 변경하여 한국 사용자에게 정확한 당일 키워드를 제공하도록 수정하였다.

**기타 안정화**: 누락된 briefing_rewards/dwell_rewards 테이블의 Alembic 마이그레이션을 추가하고, feedback 라우트에서 동적 CREATE TABLE을 제거하여 마이그레이션 기반 스키마 관리로 일원화하였다. glossary 용어 하이라이팅을 narrative_builder에 자동 주입하여, 사용자가 내러티브를 읽을 때 금융 용어가 자동으로 강조 표시되도록 하였다. narrative chart 데이터에 안전성 검사를 추가하여 잘못된 차트 데이터로 인한 프론트엔드 렌더링 오류를 방지하였다.

### Result

- 포트폴리오 API의 DB 쿼리 횟수가 N+1회에서 2회로 감소하여, 종목 10개 기준 약 82% 쿼리 감소 효과를 달성하였다.
- user_id URL 노출이 제거되어 IDOR(Insecure Direct Object Reference) 취약점이 완전히 해소되었다.
- 휴장일 거래 차단으로 비정상 거래 데이터 생성이 방지되고, 모의투자의 현실성이 향상되었다.
- Prometheus 메트릭 수집이 시작되어 인프라팀의 Grafana 대시보드와 연동, 실시간 API 성능 모니터링이 가능해졌다.
- datetime 관련 비교 오류가 해소되어 보상 시스템과 키워드 조회의 안정성이 확보되었다.

---

## Phase 4: 기능 고도화 및 안정화 (02-16)

### Situation

Phase 3까지 핵심 기능이 완성된 후, 데이터 파이프라인이 본격 운영되면서 API 안정성과 성능에 대한 고도화 요구가 높아졌다. 파이프라인이 생성한 데이터가 DB에 저장될 때 FK 제약 조건 누락으로 인해 부모 레코드 삭제 시 고아 레코드가 남는 문제가 있었다. historical_cases 테이블에 유니크 제약이 없어 동일 케이스가 중복 삽입되는 현상도 발생하였다. KIS API(한국투자증권) 클라이언트가 매 요청마다 새 인스턴스를 생성하고 토큰을 갱신하여 불필요한 네트워크 오버헤드가 있었다. API 응답 포맷이 라우트마다 제각각이어서 프론트엔드에서 일관된 에러 처리가 어려웠으며, 여러 라우트 파일에 `sys.path.insert` 해킹이 산재하여 import 경로가 불안정하였다.

### Task

- FK CASCADE 보강과 유니크 제약 추가로 데이터 무결성을 확보한다.
- KIS API 클라이언트를 싱글톤으로 재사용하고, 토큰 갱신에 동시성 제어를 적용한다.
- API 응답 포맷을 전역적으로 통일하고, 예외 처리를 표준화한다.
- sys.path 해킹을 제거하고 PYTHONPATH 기반 import로 전환한다.
- 중복 라우트 통합, broad exception 정리, JWT 보안 추가 강화를 수행한다.

### Action

**FK CASCADE 및 데이터 무결성 보강**: briefing_stocks, briefing_keywords, historical_cases 등 핵심 테이블의 FK에 `ON DELETE CASCADE`를 일괄 적용하는 마이그레이션(77라인)을 작성하였다. historical_cases에 (briefing_id, title) 유니크 제약을 추가하고, datapipeline의 writer.py에 `ON CONFLICT DO UPDATE` upsert 로직을 추가하여 중복 삽입을 방지하였다.

**KIS API 클라이언트 최적화**: `kis_service.py`를 리팩토링하여 클라이언트 인스턴스를 싱글톤으로 재사용하도록 변경하였다. 토큰 갱신 시점에 여러 요청이 동시에 갱신을 시도하는 thundering herd 문제를 `asyncio.Lock`으로 제어하여, 첫 번째 요청만 토큰을 갱신하고 나머지는 갱신 완료를 대기하도록 구현하였다. 이를 통해 KIS API 호출 시 불필요한 토큰 갱신 요청이 제거되고, 클라이언트 생성 오버헤드가 0에 수렴하였다.

**API 응답 포맷 전역 통일**: `main.py`에 전역 예외 핸들러를 등록하여 HTTPException, ValidationError, 미처리 예외 모두를 `{"status": "success|error", "data": ..., "message": ...}` 형식으로 통일하였다. `schemas/common.py`에 `ApiResponse` 제네릭 스키마를 추가하여 Swagger 문서에서도 일관된 응답 구조가 표시되도록 하였다. 이를 통해 프론트엔드에서 모든 API 응답을 동일한 패턴으로 처리할 수 있게 되었다.

**sys.path 해킹 제거**: 8개 파일에 산재하던 `sys.path.insert(0, ...)` 코드를 전부 제거하고, Dockerfile에 `ENV PYTHONPATH=/app`을 설정하여 import 경로를 표준화하였다. 이를 통해 41라인의 해킹 코드가 제거되고, 모듈 import가 Docker 환경과 로컬 환경 모두에서 일관되게 동작하도록 개선되었다.

**중복 라우트 통합 및 보안 강화**: briefing.py와 briefings.py에 중복 정의된 라우트를 briefings.py로 통합하고, briefing.py(180라인)를 삭제하였다. 각 라우트의 broad exception(`except Exception`)을 구체적인 예외 타입으로 교체하여 에러 추적을 용이하게 하였다. JWT 설정에서 토큰 만료 시간과 시크릿 키 검증을 강화하고, Redis 캐시 서비스의 에러 핸들링을 개선하였다.

**KST datetime 호환 및 스케줄러 보강**: PostgreSQL의 `TIMESTAMP WITHOUT TIME ZONE` 컬럼과 호환되도록 KST datetime을 naive로 변환하는 로직을 적용하였다. 스케줄러에 Redis 기반 분산 락을 추가하여 다중 워커 환경에서의 중복 실행을 방지하고, DB 커넥션 풀 크기를 운영 환경에 맞게 조정하였다.

### Result

- FK CASCADE 적용으로 부모 레코드 삭제 시 관련 데이터가 자동 정리되어 고아 레코드 문제가 해소되고, 유니크 제약으로 파이프라인 재실행 시에도 데이터 중복이 방지되었다.
- KIS API 클라이언트 싱글톤 전환으로 불필요한 인스턴스 생성과 토큰 갱신 요청이 제거되어, 주식 시세 조회 API의 응답시간이 안정화되었다.
- API 응답 포맷 통일로 프론트엔드의 에러 처리 코드가 단일 패턴으로 수렴하여 개발 생산성이 향상되었다.
- sys.path 해킹 제거로 Python import 경로가 표준화되어, 모듈 추가 시 path 설정 없이 바로 import가 가능해졌다.
- 중복 라우트 제거로 코드 유지보수 대상이 감소하고, broad exception 정리로 에러 원인 파악이 용이해졌다.
- Redis 분산 락으로 멀티 워커 환경에서의 스케줄러 중복 실행이 방지되었다.

---

## 기술적 의사결정 요약

| 결정 사항 | 배경 | 결과 |
|-----------|------|------|
| Spring Boot → FastAPI 통합 | 이중 백엔드 운영으로 인한 인프라 비용/유지보수 부담 | 배포 파이프라인 2개→1개, 코드량 75% 감소 |
| HS256 알고리즘 표준화 | Spring(HS384)과 FastAPI(HS256) 간 JWT 서명 불일치 | 토큰 검증 실패율 0% |
| user_id path param → JWT 추출 | URL에 사용자 ID 노출로 인한 IDOR 취약점 | 13개 파일 일괄 전환, 보안 취약점 해소 |
| N+1 → selectinload 배치 조인 | 포트폴리오 조회 시 종목 수만큼 쿼리 발생 | DB 쿼리 82% 감소 (N+1 → 2회) |
| sys.path.insert → PYTHONPATH | 8개 파일에 산재한 해킹 코드로 import 불안정 | 41라인 제거, Docker/로컬 환경 통일 |
| KIS API 싱글톤 + asyncio.Lock | 매 요청마다 클라이언트 생성 및 토큰 중복 갱신 | thundering herd 방지, 응답시간 안정화 |
| API 응답 포맷 전역 통일 | 라우트마다 다른 응답 구조로 프론트엔드 처리 복잡 | 단일 ApiResponse 패턴으로 수렴 |
| Redis 분산 락 (스케줄러) | 멀티 워커 환경에서 파이프라인 중복 실행 | 분산 환경 스케줄링 안정화 |
