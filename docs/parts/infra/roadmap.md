# Infra 로드맵

> 인프라 개선 과제를 우선순위별로 정리한다.

---

## P0 — 즉시 (이번 스프린트)

### CI/CD 파이프라인

- [ ] GitHub Actions CI 구축
  - PR 생성 시 자동 테스트 실행 (pytest, ESLint)
  - develop 머지 시 Docker 이미지 자동 빌드 + 푸시
  - prod 머지 시 deploy-test 자동 배포
- [ ] 브랜치 보호 규칙 강화
  - develop, prod 브랜치에 CI 통과 필수 조건 추가
  - PR 최소 1명 승인 + CI 통과 시만 머지 허용
- [ ] Docker 이미지 빌드 캐시 최적화
  - multi-stage 빌드에서 캐시 레이어 활용
  - GitHub Actions cache action으로 빌드 시간 단축
- [ ] deploy-test 배포 자동화
  - 현재 `make deploy` 수동 실행 → GitHub Actions에서 SSH로 자동 배포
  - 배포 완료 후 헬스 체크 + Discord 알림

---

## P1 — 다음 스프린트

### AWS 배포 준비

- [ ] Terraform 인프라 코드 완성
  - `infra/terraform/` 디렉토리에 이미 기본 구조 존재
  - VPC, ECS Fargate, RDS, ElastiCache, ECR 모듈 완성
  - 환경별 변수 파일 (`dev/terraform.tfvars`, `prod/terraform.tfvars`)
- [ ] ECR (Elastic Container Registry) 전환
  - Docker Hub (`dorae222/adelie-*`) → ECR 전환
  - GitHub Actions에서 ECR 푸시 워크플로우 추가
- [ ] ECS Fargate 배포
  - docker-compose → ECS Task Definition 변환
  - ALB (Application Load Balancer) + 타겟 그룹 설정
  - Auto Scaling 정책 (CPU/메모리 기반)
- [ ] RDS PostgreSQL 마이그레이션
  - 로컬 PostgreSQL → RDS 전환
  - Alembic migration 적용 검증
  - 데이터 마이그레이션 계획 수립

### 모니터링 고도화

- [ ] PostgreSQL exporter 추가
  - 쿼리 성능, 커넥션 풀, 테이블 크기 메트릭
  - 슬로우 쿼리 알림 (1초 이상)
- [ ] Redis exporter 추가
  - 캐시 히트/미스 비율, 메모리 사용 트렌드
  - maxmemory 도달 시 알림
- [ ] Grafana 대시보드 완성
  - 서비스별 대시보드 (인프라, 애플리케이션, 비즈니스)
  - deploy-test 컨테이너 상태 실시간 모니터링
- [ ] 알림 채널 연동
  - Grafana → Discord Webhook 알림
  - critical 알림: 즉시 전송, warning: 일일 요약

---

## P2 — 향후 계획

### 백업 전략

- [ ] PostgreSQL 자동 백업
  - 일일 pg_dump → MinIO 또는 S3 저장
  - 7일 보존 + 월간 스냅샷
  - 복원 테스트 자동화 (월 1회)
- [ ] Docker Volume 백업
  - Redis AOF, MinIO 데이터 볼륨 백업
  - 백업 스크립트 cron 등록 (현재 `infra/backup.sh` 수동)
- [ ] 재해 복구 계획 (DR)
  - LXD 호스트 장애 시 복구 절차 문서화
  - RTO (Recovery Time Objective) / RPO (Recovery Point Objective) 정의

### 로그 수집

- [ ] 중앙 로그 수집 시스템
  - Loki + Promtail 또는 ELK 스택 도입
  - Docker 컨테이너 로그 자동 수집
  - FastAPI 애플리케이션 로그 (JSON 형식)
- [ ] 로그 기반 알림
  - ERROR 레벨 로그 급증 시 알림
  - 특정 에러 패턴 (OOM, DB connection refused 등) 감지
- [ ] 로그 보존 정책
  - 7일: 전체 로그
  - 30일: ERROR 이상
  - 90일: 감사 로그

### 보안 강화

- [ ] SSL/TLS 인증서 관리 자동화
  - Cloudflare Tunnel 의존 → 직접 인증서 관리 준비 (AWS ACM)
- [ ] 네트워크 격리
  - LXD 인스턴스 간 불필요한 포트 접근 제한
  - deploy-test에서 infra-server DB 접근만 허용
- [ ] 시크릿 관리
  - `.env` 파일 기반 → AWS Secrets Manager 또는 HashiCorp Vault
  - CI/CD에서 시크릿 주입 자동화
