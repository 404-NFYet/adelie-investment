# 도형준 — 프로젝트 기여 보고서 (STAR)

> 역할: 인프라 (Docker, CI/CD)
> 기간: 2026년 2월
> 기술 스택: Docker, GitHub Actions, Terraform, LocalStack, Grafana, nginx, PostgreSQL, asyncpg

---

## Situation (상황)

- Adelie Investment 프로젝트는 React 프론트엔드, FastAPI 백엔드, 데이터 파이프라인, 챗봇 등 다수의 서비스를 Docker 기반으로 운영해야 하는 구조였으나, 초기에는 CI/CD 파이프라인, 모니터링, 인프라 자동화가 전무한 상태였다.
- 개발/스테이징/운영 환경 간의 일관성이 보장되지 않아 환경별 동작 차이 문제가 빈번하였고, 수동 배포로 인한 운영 비효율이 심각하였다.
- 코드 품질 관리, 성능 최적화, 보안 강화 등 운영 수준의 엔지니어링이 필요한 상황이었다.
- 데이터 파이프라인의 DB 저장 로직에서 타입 불일치, 날짜 처리, 데이터 정합성 등의 문제가 발생하고 있었다.

## Task (과제)

- Docker 기반 컨테이너 인프라 설계 및 운영 (dev/test/prod 환경)
- CI/CD 파이프라인 구축 (pre-commit, GitHub Actions, 자동 배포)
- 인프라 자동화 (Terraform, LocalStack) 및 모니터링 (Grafana, Discord 알림)
- 백엔드 코드 품질 개선 (라우트 정리, 예외 처리, 보안 강화)
- 데이터베이스 안정화 (FK CASCADE, 유니크 제약, 쿼리 최적화)
- 프론트엔드 빌드 최적화 및 에셋 경량화

## Action (행동)

### 주요 구현 사항

#### CI/CD 및 인프라 자동화

- **CI/CD 파이프라인 구축**: pre-commit 훅과 GitHub Actions를 결합한 CI/CD 파이프라인을 구축하였다.
  - 코드 푸시 시 자동 lint, 타입 체크, 단위 테스트 실행
  - develop/main 브랜치 머지 시 Docker 이미지 빌드
  - Docker Hub 푸시 자동화
  - deploy-test 서버(10.10.10.20) 자동 배포
- **LocalStack + Terraform 모듈 7종**: AWS 서비스를 로컬 환경에서 에뮬레이션하기 위해 LocalStack을 도입하였다.
  - Terraform 모듈: VPC, EC2, RDS, S3, IAM, CloudWatch, ALB
  - 인프라를 코드(IaC)로 관리하여 재현 가능한 환경 구성
- **Grafana 모니터링 + Discord 알림**: 서비스 모니터링 및 장애 알림 체계를 구축하였다.
  - 서비스 상태, API 응답 시간, 에러율 대시보드 구성
  - 임계값 초과 시 Discord 웹훅 자동 알림
  - Grafana 설정을 환경변수로 외부화하여 환경별 유연한 관리

#### 백엔드 코드 품질 및 보안

- **중복 라우트 통합 + broad exception 정리 + JWT 보안 강화**: FastAPI 백엔드의 코드 품질을 전반적으로 개선하였다.
  - 기능 중복 엔드포인트 통합
  - `except Exception` 광범위 예외를 구체적인 예외 클래스로 분리
  - JWT 토큰 만료 시간 설정, 리프레시 토큰 로직, 블랙리스트 등 보안 강화
- **sys.path 해킹 → PYTHONPATH 전환 (8곳)**: 코드베이스 전반에서 `sys.path.insert`로 모듈 경로를 조작하던 8곳을 PYTHONPATH 환경변수 기반으로 전환하였다.
  - Dockerfile, docker-compose, 로컬 개발 환경 모두에서 일관된 모듈 임포트 보장
  - 모듈 임포트의 예측 가능성과 유지보수성 향상
- **Google Gemini 프로바이더 추가**: MultiProviderClient에 Google Gemini 프로바이더를 추가하여 LLM 선택지를 확대하였다.
  - LLM 모델 레퍼런스 문서 작성 (모델별 특성과 용도 정리)

#### 데이터베이스 안정화

- **asyncpg executemany 타입 불일치 해결**: `briefing_stocks` 테이블에 데이터를 배치 저장하는 과정에서 발생한 asyncpg `executemany`의 타입 불일치 문제를 진단하고 해결하였다.
  - Python 타입과 PostgreSQL 컬럼 타입 간의 명시적 캐스팅 추가
- **KST datetime naive 변환**: 서버 환경이 UTC인 상황에서 KST 기준 날짜/시간 처리 표준 패턴을 정립하였다.
  - PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` 컬럼과 호환되도록 KST aware datetime을 naive로 변환
  - `kst_today()` 유틸리티 함수 도입으로 `date.today()` 사용 금지
- **keywords N+1 쿼리 → 배치 조인**: 키워드 목록 조회 시 발생하던 N+1 쿼리 문제를 배치 조인으로 해결하였다.
  - API 응답 시간 대폭 개선
  - 헬스체크 엔드포인트에서 DB 연결 실패 시 503 상태코드 반환
- **FK CASCADE 보강 + historical_cases 유니크 제약 + writer upsert**: 데이터 정합성과 파이프라인 안정성을 확보하였다.
  - 테이블 간 외래키 관계에 CASCADE 삭제 보강
  - `historical_cases` 테이블에 유니크 제약 추가로 중복 방지
  - `writer.py` 데이터 저장 로직을 upsert(INSERT ON CONFLICT UPDATE) 패턴으로 전환

#### 프론트엔드 및 Docker 최적화

- **penguin-3d 8.2MB → 330KB WebP**: 프론트엔드의 3D 펭귄 에셋을 WebP로 변환하여 96% 용량 절감하였다.
  - nginx 보안 헤더 추가 (X-Frame-Options, X-Content-Type-Options, CSP)
  - Vite 빌드 설정 최적화로 번들 사이즈 개선
- **.dockerignore + Docker 로그 로테이션**: Docker 운영 환경을 최적화하였다.
  - Docker 빌드 컨텍스트 최적화로 빌드 시간 단축
  - 로그 로테이션 설정 추가로 디스크 공간 문제 예방
  - LLM API 호출 재시도 로직 추가
- **대시보드 피드백 관리 탭 추가**: 관리자 대시보드에 사용자 피드백 조회/관리 기능을 확충하였다.

### 기술적 의사결정

- **Docker Compose 멀티 환경 전략**: `docker-compose.dev.yml`, `docker-compose.test.yml`, `docker-compose.prod.yml`로 환경을 분리하여, 각 환경에 최적화된 설정을 적용하면서도 동일한 Docker 이미지를 사용하여 환경 간 일관성을 보장하였다.
- **PYTHONPATH 기반 모듈 관리**: `sys.path.insert` 해킹 대신 PYTHONPATH 환경변수를 사용하는 표준 패턴을 도입하여, 모든 실행 환경에서 일관된 모듈 임포트를 보장하였다.
- **upsert 패턴 표준화**: 데이터 파이프라인에서 DB에 데이터를 저장할 때 INSERT + ON CONFLICT UPDATE 패턴을 표준으로 채택하여, 파이프라인 재실행이나 중복 데이터 유입에 대한 내성을 확보하였다.
- **WebP 이미지 포맷 채택**: 프론트엔드 에셋에 WebP 포맷을 적용하여 이미지 품질 손실 없이 용량을 대폭 절감하는 최적화 전략을 수립하였다.
- **Grafana + Discord 알림 기반 모니터링**: 별도의 유료 모니터링 서비스 대신 오픈소스 Grafana와 Discord 웹훅을 조합하여 비용 효율적인 모니터링 및 알림 체계를 구축하였다.

## Result (결과)

### 정량적 성과

| 지표 | 수치 |
|------|------|
| 커밋 수 | 208개 |
| 코드 변경량 | +171,919 / -14,268 라인 |
| 활동일 수 | 12일 |
| Docker Compose 환경 | 3종 (dev / test / prod) |
| Terraform 모듈 | 7종 |
| 에셋 용량 절감 | 96% (8.2MB → 330KB) |
| sys.path 해킹 전환 | 8곳 |

### 정성적 성과

- CI/CD 파이프라인 구축으로 코드 푸시부터 배포까지의 전체 프로세스를 자동화하여, 팀의 배포 주기를 단축하고 수동 배포 오류를 제거하였다.
- Docker 기반 인프라 표준화로 환경별 동작 차이 문제를 근본적으로 해소하고, 팀원 전체가 동일한 개발 환경에서 작업할 수 있게 하였다.
- 데이터베이스 안정화 작업(FK CASCADE, 유니크 제약, upsert, N+1 해결)을 통해 데이터 정합성과 API 성능을 동시에 개선하였다.
- 보안 헤더 추가, JWT 강화, broad exception 정리 등을 통해 서비스의 보안 수준을 향상시켰다.
- 인프라와 백엔드 코드 품질 양 측면에서 프로젝트의 운영 안정성을 크게 높이는 기반을 마련하였다.
