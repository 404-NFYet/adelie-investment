# 파트별 개선 로드맵

> 대상 독자: 전체 팀원
> 각 파트별 개선 과제를 우선순위(P0/P1/P2)로 구분하여 정리합니다.

---

## 우선순위 기준

| 등급 | 의미 | 목표 시점 |
|------|------|-----------|
| **P0** | 즉시 착수 — 서비스 품질/안정성에 직결 | 2주 이내 |
| **P1** | 중기 개선 — 사용자 경험 및 운영 효율 | 1~2개월 |
| **P2** | 장기 투자 — 확장성, 유지보수성 향상 | 분기 내 |

---

## Frontend (손영진)

담당 디렉토리: `frontend/`
기술 스택: React 19 + Vite, Tailwind CSS, mobile-first (max-width: 480px)

### P0 — 즉시 착수

| 과제 | 설명 |
|------|------|
| UI 디자인 리뉴얼 | 일관된 디자인 시스템 구축 (색상, 타이포, 스페이싱 토큰 정리). 현재 컴포넌트별 산발적 스타일 통일 |
| 반응형 확장 | 태블릿(768px) / 데스크톱(1280px) 레이아웃 대응. 현재 480px 전용 → 미디어쿼리 확장 |

### P1 — 중기 개선

| 과제 | 설명 |
|------|------|
| 접근성(a11y) 개선 | ARIA 속성 보강, 키보드 네비게이션, 포커스 관리. WAI-ARIA 기본 가이드라인 준수 |
| 성능 최적화 | 코드 스플리팅 개선 (lazy 경계 세분화), 이미지 최적화, Lighthouse 점수 90+ 목표 |

### P2 — 장기 투자

| 과제 | 설명 |
|------|------|
| Storybook 도입 | 공통 컴포넌트(`common/`) 대상 Storybook 카탈로그 구축. 디자인 시스템 문서화 겸용 |
| 프론트엔드 테스트 | Vitest + Testing Library 기반 단위/통합 테스트. 주요 페이지 렌더링 + 사용자 인터랙션 커버 |

---

## Chatbot (정지훈)

담당 디렉토리: `chatbot/`
기술 스택: LangGraph agent + tools, SSE streaming, LangChain

### P0 — 즉시 착수

| 과제 | 설명 |
|------|------|
| 에이전트 안정성 | 에러 핸들링 강화 (LLM 타임아웃, 도구 실패 시 graceful fallback), 자동 재시도 로직 |
| 프롬프트 품질 개선 | 튜터 프롬프트 반복 테스트 및 개선. 할루시네이션 감소, 응답 일관성 향상 |

### P1 — 중기 개선

| 과제 | 설명 |
|------|------|
| 도구 확장 | 차트 생성 도구 고도화, 비교 분석 도구 정밀화. 사용자 질문 패턴 분석 기반 |
| 대화 이력 영속화 | 현재 메모리 기반 → DB/Redis 저장으로 전환. 세션 간 대화 이력 유지 |

### P2 — 장기 투자

| 과제 | 설명 |
|------|------|
| 모델 전환 유연성 | Claude/GPT 동적 선택 기능. 비용/성능 기반 자동 라우팅 검토 |
| 멀티턴 컨텍스트 최적화 | 긴 대화 시 컨텍스트 윈도우 관리 (요약, 슬라이딩 윈도우 등) |

---

## Data Pipeline (안례진)

담당 디렉토리: `datapipeline/`
기술 스택: LangGraph 18노드 파이프라인, asyncpg, OpenAI/Perplexity/Claude

### P0 — 즉시 착수

| 과제 | 설명 |
|------|------|
| 프롬프트 품질 향상 | 환각(hallucination) 감소 — hallucination_check, final_hallucination 노드 정밀화 |
| 크롤러 안정성 | 네이버 뉴스/리서치, pykrx 장애 대응. 재시도 로직, fallback 소스, 알림 추가 |

### P1 — 중기 개선

| 과제 | 설명 |
|------|------|
| 모델 비용 최적화 | gpt-4o-mini 활용 극대화. 노드별 모델 선택 기준 정리, 비용 대비 품질 트레이드오프 |
| 파이프라인 모니터링 | 노드별 실행 시간, 성공/실패율, LLM 토큰 사용량 대시보드 (LangSmith 활용) |

### P2 — 장기 투자

| 과제 | 설명 |
|------|------|
| 새 데이터 소스 추가 | 해외 뉴스, 공시 데이터, SNS 감성 분석 등 소스 확장 |
| 파이프라인 스케줄링 자동화 | 현재 수동/cron → Airflow 또는 자체 스케줄러로 자동화. 장애 시 재실행 |

---

## Backend (허진서)

담당 디렉토리: `fastapi/`
기술 스택: FastAPI, SQLAlchemy async, JWT auth, Alembic

### P0 — 즉시 착수

| 과제 | 설명 |
|------|------|
| DB 쿼리 최적화 | N+1 문제 해결 (eager loading, joinedload 적용). slow query 식별 및 인덱스 추가 |
| API 문서화 | Swagger(OpenAPI) 정리 — 각 라우트에 summary, description, response_model 명시 |

### P1 — 중기 개선

| 과제 | 설명 |
|------|------|
| Alembic 워크플로우 개선 | 마이그레이션 충돌 방지 전략, 팀원간 마이그레이션 브랜치 병합 가이드 |
| 캐싱 전략 | Redis TTL 기반 캐싱 — 오늘의 키워드, 케이스 목록 등 자주 조회 데이터 대상 |

### P2 — 장기 투자

| 과제 | 설명 |
|------|------|
| API 버저닝 | `/api/v2` 도입 검토. 하위 호환성 유지하며 스키마 개선 |
| 로깅 표준화 | structlog 등 구조화 로깅 도입. 요청 ID 기반 추적 가능하도록 |
| Flyway 검토 | Alembic 대안으로 Flyway 도입 가능성 평가 (JVM 기반 팀 합류 시) |

---

## Infra (도형준)

담당 디렉토리: `lxd/`, `docker-compose.*.yml`, `.github/`
기술 스택: Docker, LXD, GitHub Actions, AWS 준비

### P0 — 즉시 착수

| 과제 | 설명 |
|------|------|
| CI/CD 파이프라인 | GitHub Actions 구축 — PR 시 자동 테스트(lint + pytest), develop 머지 시 자동 빌드/배포 |

### P1 — 중기 개선

| 과제 | 설명 |
|------|------|
| AWS 배포 준비 | ECS(Fargate) 또는 EKS 검토. Terraform/CDK IaC 기반 인프라 코드화 |
| 모니터링 | Prometheus + Grafana 또는 경량 대안(Uptime Kuma 등). 서비스 헬스체크, 응답시간 추적 |

### P2 — 장기 투자

| 과제 | 설명 |
|------|------|
| 백업 자동화 | PostgreSQL DB 스냅샷 자동화 (pg_dump cron 또는 AWS RDS 스냅샷) |
| 로그 수집 | ELK(Elasticsearch+Logstash+Kibana) 또는 Loki+Grafana. 컨테이너 로그 중앙 수집 |

---

## 전체 우선순위 요약

```
P0 (즉시)
├── Frontend: UI 디자인 시스템, 반응형 확장
├── Chatbot: 에이전트 안정성, 프롬프트 품질
├── Pipeline: 환각 감소, 크롤러 안정성
├── Backend: N+1 쿼리 최적화, API 문서화
└── Infra: CI/CD (GitHub Actions)

P1 (중기)
├── Frontend: 접근성, 성능 최적화
├── Chatbot: 도구 확장, 대화 이력 영속화
├── Pipeline: 모델 비용 최적화, 모니터링
├── Backend: Alembic 워크플로우, Redis 캐싱
└── Infra: AWS 배포, 모니터링

P2 (장기)
├── Frontend: Storybook, 테스트
├── Chatbot: 모델 동적 선택, 컨텍스트 최적화
├── Pipeline: 새 데이터 소스, 스케줄링 자동화
├── Backend: API 버저닝, 로깅 표준화
└── Infra: 백업 자동화, 로그 수집
```
