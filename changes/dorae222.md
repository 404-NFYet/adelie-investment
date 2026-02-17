# 도형준 (dorae222) — 프로젝트 변경이력

> 역할: 인프라 개발
> 기간: 2026-01-20 ~ 현재 (개발 진행 중)
> 기술 스택: Docker, LXD, Nginx, Prometheus, Grafana, GitHub Actions, Terraform, LocalStack, Streamlit

---

## Phase 1: 프로젝트 초기 구축 (2026-01-20 ~ 02-06)

### Situation

Adelie Investment 프로젝트가 시작되었으나, 5인 개발팀이 동시에 작업할 수 있는 개발 인프라가 전무한 상태였다. 각 팀원이 로컬 머신에서 독립적으로 개발해야 하는 환경이었고, 공유 데이터베이스나 배포 서버가 준비되지 않아 협업 효율이 낮았다. 물리 서버 1대(1.8TB NVMe, 84GB RAM)를 팀 전체가 공유해야 하는 자원 제약 상황에서, 격리된 개발 환경과 공유 인프라를 동시에 구성해야 했다.

### Task

- 물리 서버 위에 팀원별 격리된 개발 환경 구축
- PostgreSQL, Redis, MinIO 등 공유 인프라 서비스 셋업
- Docker 기반 서비스 오케스트레이션 설계
- 배포 테스트 서버 구성 및 초기 배포 파이프라인 수립

### Action

**LXD 7-컨테이너 클러스터를 설계하고 구축하였다.** 물리 서버 1대 위에 LXD를 활용하여 역할별 7개 컨테이너(infra-server, deploy-test, dev-yj99son, dev-j2hoon10, dev-ryejinn, dev-jjjh02, dev-hj)를 배치하였다. 인프라 서버(10.10.10.10)에는 PostgreSQL, Redis, MinIO를, 배포 테스트 서버(10.10.10.20)에는 프로덕션 환경을, 나머지 5개 컨테이너에는 팀원별 개발 환경을 할당하였다. 각 컨테이너의 CPU/RAM을 역할에 따라 차등 배분(AI 개발: 4CPU/12GB, 일반 개발: 4CPU/8GB, 배포: 16CPU/32GB)하고, 스토리지 quota를 설정(인프라 300GB, 배포 200GB, 개발 각 150GB)하여 자원 충돌을 방지하였다.

**환경 자동 구성 스크립트를 작성하였다.** `setup-dev-env.sh`(288라인)로 LXD 컨테이너 내 개발 환경(Docker, Node.js, Python venv, Git 설정)을 자동 프로비저닝하고, `setup-hdd-pool.sh`(177라인)로 스토리지 풀 관리를, `verify-dev-env.sh`(133라인)로 환경 검증을 자동화하였다. 하이브리드 모드를 지원하여 기존 환경을 파괴하지 않고 증분 설정이 가능하도록 설계하였다.

**Docker Compose 멀티 환경 전략을 수립하였다.** `docker-compose.dev.yml`(개발), `docker-compose.test.yml`(테스트), `docker-compose.prod.yml`(운영) 3종의 Compose 파일을 분리하여, 동일한 Docker 이미지를 사용하면서도 환경별 최적화된 설정(리소스 제한, 볼륨 마운트, 네트워크 구성)을 적용하였다. 프로덕션 환경에서는 PostgreSQL(16GB/4CPU), Redis(2GB/2CPU), MinIO, frontend, backend-api, ai-pipeline 등 6개 서비스를 오케스트레이션하였다.

### Result

- LXD 7개 컨테이너 클러스터 가동: 총 34CPU / 84GB RAM / 1.8TB NVMe 공유
- 5인 팀원 전원에게 격리된 개발 환경 제공 완료
- Docker Compose 3종(dev/test/prod) 환경 분리로 개발-배포 파이프라인 기반 마련
- 환경 자동 구성 스크립트 3종(setup-dev-env, setup-hdd-pool, verify-dev-env) — 신규 팀원 온보딩 소요 시간 최소화

---

## Phase 2: 핵심 기능 구현 지원 (2026-02-06 ~ 02-12)

### Situation

Phase 1에서 기본 인프라가 구축되었으나, 각 파트(프론트엔드, 백엔드, 파이프라인, 챗봇)의 핵심 기능 개발이 본격화되면서 인프라 측면의 지원 요구가 급증하였다. Spring Boot 인증 서버와 FastAPI 백엔드가 병존하여 Docker Compose와 배포 설정이 복잡해졌고, 파이프라인 코드의 모듈 임포트 경로 문제로 Docker 환경에서의 실행 실패가 빈번하였다. GitHub 워크플로우와 협업 프로세스도 정비가 필요한 상태였다.

### Task

- Spring Boot 서비스 제거 후 Docker/배포 설정 정리
- 프로젝트 문서 체계 수립 및 팀원별 개발 가이드 작성
- GitHub 워크플로우(PR/이슈 템플릿, Discord 알림) 개선
- LXD 서버 역할 재편 및 리소스 재배분

### Action

**Spring Boot 서비스를 Docker 및 배포 설정에서 완전히 제거하였다.** 인증 기능이 FastAPI로 통합됨에 따라 docker-compose 3종(dev/test/prod)과 Makefile에서 Spring Boot 관련 서비스 정의, 빌드 타겟, 배포 스크립트를 모두 삭제하였다. 관련 문서(.gitignore, CLAUDE.md, README, 배포 가이드 등 18개 파일)를 일괄 업데이트하여 아키텍처 변경을 반영하였다.

**프로젝트 문서를 전면 재구성하였다.** 기존 숫자 prefix 기반 평면 구조를 카테고리별 폴더 구조(architecture, getting-started, guides, reference, parts)로 개편하고, 팀원별 단일 통합 가이드 5종을 작성하였다. 모듈별 개발 가이드(backend, chatbot, frontend, pipeline, infra)를 18개 문서로 신규 작성하여, 각 파트 담당자가 해당 모듈의 아키텍처, 의존성, 로드맵을 한 곳에서 참조할 수 있도록 하였다. Contributing 가이드를 전면 개편하여 `dev/{part}` 브랜치 전략과 모듈 소유권(CODEOWNERS)을 재정의하였다.

**GitHub 협업 인프라를 개선하였다.** PR/이슈 템플릿을 체크리스트 기반으로 개편하고, GitHub Actions 워크플로우에 브랜치별 Discord Embed 알림을 추가하여 팀원이 커밋/배포 상태를 실시간으로 파악할 수 있도록 하였다. CODEOWNERS 파일을 역할 재편에 맞추어 업데이트하였다.

**LXD 서버를 역할 변경에 맞추어 재구성하였다.** 안례진(ryejinn)의 역할 전환(QA → Pipeline)에 따라 `dev-ryejinn` 컨테이너를 `dev-qa.yml`(2CPU/4GB)에서 `dev-ai.yml`(4CPU/12GB)으로 승격하고, deploy-test 서버의 RAM을 실사용량(~1.3GB) 대비 과잉이던 64GB에서 32GB로 축소하여 다른 컨테이너에 재배분하였다.

### Result

- Spring Boot 관련 설정 완전 제거로 Docker Compose 복잡도 감소 (서비스 수 6개 → 5개)
- 프로젝트 문서 전면 재구성: 신규 문서 24종 작성, 기존 문서 18개 업데이트
- GitHub 워크플로우 개선: Discord Embed 알림, PR/이슈 템플릿 개편, CODEOWNERS 갱신
- LXD 리소스 재배분으로 파이프라인 개발 환경 3배 메모리 확보 (4GB → 12GB)

---

## Phase 3: 모니터링 & 통합 (2026-02-12 ~ 02-14)

### Situation

핵심 기능 개발이 진행되면서 deploy-test 서버에 실제 서비스가 올라갔으나, 서버/컨테이너 상태를 파악할 수 있는 모니터링 체계가 없었다. 장애가 발생해도 팀원이 직접 SSH 접속하여 `docker ps`와 `docker logs`를 확인해야 했고, 서버 리소스(CPU, 메모리, 디스크) 사용량을 사전에 파악할 수 없어 성능 이슈가 뒤늦게 발견되는 상황이 반복되었다. 또한 개발 편의를 위한 운영 도구(DB 조회, API 테스트, 배포 관리)가 부재하여 인프라 담당자에게 운영 요청이 집중되었다.

### Task

- Prometheus + Grafana 기반 모니터링 인프라 구축
- 서버/컨테이너/API 메트릭 수집 및 대시보드 구성
- 팀원 자율 운영이 가능한 관리 대시보드 개발
- Docker 운영 환경 최적화 (로그 관리, 빌드 개선)

### Action

**Prometheus + Grafana 모니터링 스택을 구축하고 대시보드 3종을 구성하였다.** Prometheus에서 3개 scrape job(node-exporter 7대, cAdvisor 2대, FastAPI 메트릭 1대)으로 메트릭을 수집하고, Grafana에서 다음 3종의 대시보드를 구성하였다.
- **Node Exporter 대시보드**: LXD 7개 컨테이너의 CPU, 메모리, 디스크, 네트워크 모니터링 (799라인 JSON)
- **cAdvisor 대시보드**: Docker 컨테이너별 리소스 사용량 추적 (511라인 JSON)
- **Adelie Overview 대시보드**: 서비스 전체 현황 — API 응답 시간, 에러율, 요청량 (1,187라인 JSON)

Prometheus의 데이터 보존 기간은 30일로 설정하고, Grafana 설정을 환경변수(`GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`)로 외부화하여 환경별 유연한 관리를 가능하게 하였다. FastAPI backend-api에 `/metrics` 엔드포인트를 노출하여 애플리케이션 레벨 메트릭까지 수집하였다.

**Streamlit 기반 운영 대시보드를 개발하였다.** 6개 페이지(팀원 서버 관리, 배포 관리, DB 뷰어, API 테스터, 모니터링, 피드백 관리)로 구성된 통합 운영 대시보드를 구현하였다. SSH 연결을 통한 원격 서버 상태 확인, Docker 컨테이너 관리, PostgreSQL 데이터 조회, API 엔드포인트 테스트, Grafana 대시보드 임베딩 등의 기능을 한 화면에서 제공하여, 팀원이 SSH 명령어 없이도 서비스 상태를 파악하고 관리할 수 있도록 하였다. Dockerfile과 docker-compose를 작성하여 대시보드 자체도 컨테이너로 배포 가능하게 하였다.

**Docker 운영 환경을 최적화하였다.** `.dockerignore` 파일을 추가하여 빌드 컨텍스트에서 불필요한 파일(node_modules, .git, .env 등)을 제외하였다. 프로덕션 docker-compose의 모든 서비스에 JSON 파일 로그 로테이션(max-size 10MB, max-file 3)을 일괄 적용하여 디스크 공간 문제를 예방하였다. docker-compose.dev.yml을 리팩토링하여 프론트엔드 개발 모드와 Docker Hub 이미지 태그 관리를 개선하였다.

### Result

- Prometheus 모니터링: 7개 노드 + 2개 cAdvisor + 1개 FastAPI 메트릭 = 총 10개 scrape target
- Grafana 대시보드 3종 구성 (합계 2,497라인 JSON 설정)
- Streamlit 운영 대시보드: 6개 페이지, 1,725라인 코드 (총 17개 파일)
- Docker 로그 로테이션 적용으로 서비스당 최대 30MB 디스크 사용량 제한 (6개 서비스 기준 최대 180MB)

---

## Phase 4: CI/CD & IaC 고도화 (2026-02-14 ~ 02-17)

### Situation

서비스가 안정화 단계에 진입하면서, 수동 배포의 한계가 명확해졌다. 코드 변경 후 Docker 이미지 빌드, 레지스트리 푸시, deploy-test 서버 접속, compose 재시작까지 매번 5단계 이상의 수동 작업이 필요했으며, 코드 품질 검증(lint, 테스트)도 개인 재량에 의존하고 있었다. 또한 향후 AWS 이전을 대비한 인프라 코드화(IaC)와, 프론트엔드 에셋 최적화, 보안 강화 등의 운영 수준 엔지니어링이 필요한 상황이었다.

### Task

- CI/CD 파이프라인 구축 (코드 푸시부터 배포/알림까지 자동화)
- LocalStack + Terraform 기반 AWS 인프라 코드화
- 프론트엔드 에셋 최적화 및 Nginx 보안 강화
- 프로젝트 전체 문서 통합 및 STAR 보고서 작성

### Action

**CI/CD 파이프라인을 2단계로 구축하였다.** 먼저 pre-commit 훅(`.pre-commit-config.yaml`)으로 커밋 시점에 코드 포맷/lint를 자동 검사하도록 하고, GitHub Actions CI 워크플로우(`ci.yml`, 140라인)에서 PR 생성 시 Python lint(ruff), 프론트엔드 lint, 백엔드 테스트(pytest + PostgreSQL/Redis 서비스 컨테이너), 프론트엔드 빌드 체크를 자동 실행하도록 하였다. Deploy 워크플로우(`deploy.yml`, 148라인)에서는 develop 브랜치 푸시 시 Docker 이미지 3종(frontend, backend-api, ai-pipeline) 빌드 → Docker Hub 푸시 → SSH를 통한 deploy-test 서버 자동 배포 → 헬스체크(5회 재시도) → Discord Embed 알림(성공/실패 분기, 작성자 역할 자동 매핑)까지 전 과정을 자동화하였다.

**LocalStack + Terraform으로 AWS 인프라를 코드화하였다.** LocalStack Docker 환경을 구성하여 AWS 서비스를 로컬에서 에뮬레이션하고, Terraform 모듈 8종(VPC, Bastion, ECR, ECS, RDS, ElastiCache, S3, Secrets Manager)을 작성하여 전체 AWS 인프라를 IaC로 관리할 수 있도록 하였다. 각 모듈은 `main.tf`, `variables.tf`, `outputs.tf`로 구성되며, `environments/localstack/main.tf`(177라인)에서 모듈을 조합하여 전체 인프라를 한 번에 프로비저닝할 수 있도록 설계하였다. Grafana에 Discord 알림 연동(contact_points, notification_policies)을 추가하여 모니터링 임계값 초과 시 자동 알림을 발송하도록 하였다.

**프론트엔드 에셋을 대폭 경량화하고 Nginx 보안을 강화하였다.** 3D 펭귄 마스코트 이미지를 8.2MB PNG에서 330KB WebP로 변환하여 96% 용량을 절감하였다. Nginx 설정에 보안 헤더(X-Frame-Options, X-Content-Type-Options, Content-Security-Policy)를 추가하고, Vite 빌드 설정을 최적화하여 프론트엔드 번들 사이즈를 개선하였다.

**프로젝트 문서를 최종 통합하였다.** 기존에 분산되어 있던 35개 문서(5,274라인)를 삭제하고 통합 가이드로 대체하는 대대적인 문서 정리를 수행하였다. 팀원 5인의 STAR 보고서를 작성하고, AWS IAM 권한 가이드(908라인)와 LocalStack 사용 가이드(645라인)를 신규 작성하였다. README에 아키텍처 다이어그램을 추가하고 챗봇 설계 문서를 보완하였다.

### Result

- CI/CD 전자동화: 코드 푸시 → lint/테스트 → 이미지 빌드 → 배포 → 헬스체크 → Discord 알림 (6단계 자동 수행)
- Terraform IaC 모듈 8종: VPC, Bastion, ECR, ECS, RDS, ElastiCache, S3, Secrets Manager
- 에셋 최적화: 마스코트 이미지 96% 절감 (8.2MB → 330KB)
- Nginx 보안 헤더 3종 추가 (XFO, XCTO, CSP)
- 프로젝트 문서 통합: 분산 문서 35개 삭제 → 통합 가이드 대체, STAR 보고서 5인분 작성
- GitHub Actions 워크플로우 2종(CI 140라인, Deploy 148라인) + pre-commit 훅 구성

---

## 전체 정량적 성과 요약

| 지표 | 수치 |
|------|------|
| 총 커밋 수 | 약 63개 |
| 활동 기간 | 2026-01-20 ~ 02-17 (약 4주) |
| LXD 컨테이너 | 7개 (합계 34CPU / 84GB RAM) |
| Docker Compose 환경 | 3종 (dev / test / prod) |
| 프로덕션 서비스 | 6개 (postgres, redis, minio, frontend, backend-api, ai-pipeline) |
| Prometheus scrape target | 10개 (node 7 + cAdvisor 2 + FastAPI 1) |
| Grafana 대시보드 | 3종 (2,497라인 JSON) |
| Terraform 모듈 | 8종 (VPC, Bastion, ECR, ECS, RDS, ElastiCache, S3, Secrets) |
| Streamlit 대시보드 | 6페이지, 1,725라인 |
| GitHub Actions 워크플로우 | 2종 (CI + Deploy) |
| 에셋 용량 절감 | 96% (8.2MB → 330KB) |
| Docker 로그 로테이션 | 서비스당 최대 30MB (10MB x 3 파일) |
| 문서 작성/개편 | 신규 24종, 업데이트 18종, 정리(삭제) 35종 |
| STAR 보고서 | 5인분 작성 |
