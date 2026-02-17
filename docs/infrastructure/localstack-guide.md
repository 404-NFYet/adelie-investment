# LocalStack 운영 가이드

## 1. 개요

### LocalStack이란?

LocalStack은 AWS 클라우드 서비스를 로컬 환경에서 에뮬레이션하는 도구입니다. 실제 AWS 계정 없이도 S3, ECR, ECS, Secrets Manager 등의 서비스를 로컬에서 테스트할 수 있습니다.

### 왜 사용하는가?

| 이유 | 설명 |
|------|------|
| **비용 절감** | AWS 리소스를 생성하지 않으므로 비용이 발생하지 않음 |
| **빠른 피드백** | 인프라 변경을 몇 초 만에 적용/확인 가능 |
| **안전한 실험** | 실제 환경에 영향 없이 Terraform 코드를 검증 |
| **오프라인 개발** | 인터넷 없이도 AWS 서비스 연동 코드 개발 가능 |
| **CI 파이프라인** | GitHub Actions에서 통합 테스트 시 AWS 모킹 용도로 활용 |

### 프로젝트에서의 활용

Adelie Investment 프로젝트에서 LocalStack은 다음 용도로 사용합니다:

1. **Terraform 코드 검증** — `infra/terraform/modules/` 의 모든 모듈을 실제 배포 전에 로컬에서 테스트
2. **ECR 이미지 푸시/풀 테스트** — 컨테이너 이미지 레지스트리 워크플로우 검증
3. **Secrets Manager 연동 테스트** — API 키 주입 로직 검증
4. **S3 오브젝트 스토리지 테스트** — 리포트 파일 업로드/다운로드 검증

---

## 2. 설치 및 구동

### 사전 요구사항

- Docker 및 Docker Compose
- AWS CLI v2 (또는 `awslocal` — LocalStack CLI)
- Terraform >= 1.5.0

### awslocal 설치

```bash
# pip로 설치 (권장)
pip install awscli-local

# 또는 brew (macOS)
brew install localstack/tap/awscli-local
```

`awslocal`은 `aws` CLI를 LocalStack 엔드포인트(localhost:4566)로 자동 라우팅하는 래퍼입니다. `aws --endpoint-url=http://localhost:4566`을 매번 입력할 필요가 없습니다.

### LocalStack 구동

```bash
# 프로젝트 루트에서 Makefile 사용 (권장)
make localstack-up

# 또는 직접 docker compose 사용
cd infra/localstack && docker compose up -d
```

### 구동 확인

```bash
# 헬스 체크
curl http://localhost:4566/_localstack/health | jq

# 실행 중인 서비스 확인
awslocal sts get-caller-identity
```

정상 출력 예시:
```json
{
  "UserId": "AKIAIOSFODNN7EXAMPLE",
  "Account": "000000000000",
  "Arn": "arn:aws:iam::000000000000:root"
}
```

### LocalStack 중지

```bash
make localstack-down

# 또는
cd infra/localstack && docker compose down
```

### 설정 파일

LocalStack 설정은 `infra/localstack/docker-compose.yml`에 정의되어 있습니다:

```yaml
services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"           # Gateway 포트 (모든 AWS 서비스)
      - "4510-4559:4510-4559" # 서비스별 개별 포트 (선택적)
    environment:
      SERVICES: s3,secretsmanager,ecr,ecs,rds,elasticache,ec2,iam,sts,cloudwatch,logs,events
      DEFAULT_REGION: ap-northeast-2
      DOCKER_HOST: unix:///var/run/docker.sock
      PERSISTENCE: 1          # 컨테이너 재시작 시 데이터 유지
    volumes:
      - localstack-data:/var/lib/localstack
      - /var/run/docker.sock:/var/run/docker.sock
```

| 환경변수 | 값 | 설명 |
|----------|-----|------|
| `SERVICES` | `s3,secretsmanager,ecr,...` | 활성화할 AWS 서비스 목록 |
| `DEFAULT_REGION` | `ap-northeast-2` | 기본 리전 (서울, 프로덕션과 동일) |
| `PERSISTENCE` | `1` | 컨테이너 재시작 후에도 상태 유지 |
| `DOCKER_HOST` | `unix:///var/run/docker.sock` | ECS 등 Docker-in-Docker 기능 필요 시 |

---

## 3. Terraform 연동

### 디렉토리 구조

```
infra/terraform/
├── environments/
│   ├── localstack/     # LocalStack 전용 진입점
│   │   └── main.tf
│   └── dev/            # 실제 AWS dev 환경
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── terraform.tfvars.example
└── modules/            # 공통 모듈 (환경에 무관하게 재사용)
    ├── vpc/
    ├── bastion/
    ├── ecr/
    ├── ecs/
    ├── rds/
    ├── elasticache/
    ├── s3/
    └── secrets/
```

`localstack/main.tf`와 `dev/main.tf`는 동일한 모듈(`../../modules/*`)을 참조하되, provider 설정만 다릅니다. 따라서 LocalStack에서 검증된 모듈은 실제 AWS에서도 동일하게 동작합니다.

### Provider 설정 (LocalStack 전용)

`infra/terraform/environments/localstack/main.tf`의 핵심 설정:

```hcl
provider "aws" {
  region                      = "ap-northeast-2"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3             = "http://localhost:4566"
    secretsmanager = "http://localhost:4566"
    ecr            = "http://localhost:4566"
    ecs            = "http://localhost:4566"
    rds            = "http://localhost:4566"
    elasticache    = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    iam            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    cloudwatchlogs = "http://localhost:4566"
    events         = "http://localhost:4566"
    elbv2          = "http://localhost:4566"
  }
}

# LocalStack은 로컬 상태 파일 사용 (S3 backend 아님)
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
```

**주요 차이점 (vs dev 환경)**:
- `access_key`/`secret_key`: `"test"` 고정값 (인증 불필요)
- `skip_*`: 자격 증명 검증, 메타데이터 API 체크 건너뜀
- `endpoints`: 모든 서비스가 `localhost:4566`으로 라우팅
- `backend`: S3가 아닌 로컬 파일 (`terraform.tfstate`)

### Terraform 실행

```bash
# 1단계: LocalStack 구동
make localstack-up

# 2단계: Terraform 초기화 (ENV=localstack이 기본값)
make terraform-init

# 3단계: 실행 계획 확인
make terraform-plan

# 4단계: 인프라 적용
make terraform-apply
```

`ENV` 변수를 통해 대상 환경을 전환할 수 있습니다:

```bash
# LocalStack (기본값)
make terraform-init                    # ENV=localstack
make terraform-plan

# 실제 AWS dev 환경
make terraform-init ENV=dev
make terraform-plan ENV=dev
make terraform-apply ENV=dev
```

### Terraform 실행 결과 확인

```bash
# 적용 후 출력값 확인
cd infra/terraform/environments/localstack
terraform output

# 예시 출력:
# alb_url = "adelie-alb-xxxxx.elb.localhost.localstack.cloud"
# bastion_ip = "10.0.1.x"
# ecr_urls = { "frontend" = "000000000000.dkr.ecr.ap-northeast-2.localhost.localstack.cloud/adelie-frontend", ... }
# rds_endpoint = "localhost"
# redis_endpoint = "localhost"
# s3_buckets = ["adelie-naver-reports", "adelie-extracted-data"]
```

### 인프라 삭제

```bash
make terraform-destroy
```

---

## 4. 서비스별 테스트

### 4.1 ECR (Elastic Container Registry)

```bash
# 리포지토리 생성 (Terraform 적용 시 자동 생성됨)
awslocal ecr create-repository --repository-name adelie-frontend
awslocal ecr create-repository --repository-name adelie-backend-api
awslocal ecr create-repository --repository-name adelie-ai-pipeline

# 리포지토리 목록 확인
awslocal ecr describe-repositories

# 이미지 푸시 테스트
# 1) 로그인 토큰 받기
awslocal ecr get-login-password | docker login --username AWS --password-stdin localhost.localstack.cloud:4566

# 2) 이미지 태그
docker tag dorae222/adelie-frontend:latest localhost.localstack.cloud:4566/adelie-frontend:latest

# 3) 이미지 푸시
docker push localhost.localstack.cloud:4566/adelie-frontend:latest

# 이미지 목록 확인
awslocal ecr list-images --repository-name adelie-frontend

# 리포지토리 삭제
awslocal ecr delete-repository --repository-name adelie-frontend --force
```

### 4.2 S3 (Simple Storage Service)

```bash
# 버킷 생성
awslocal s3 mb s3://adelie-naver-reports
awslocal s3 mb s3://adelie-extracted-data

# 버킷 목록 확인
awslocal s3 ls

# 파일 업로드
echo '{"test": "data"}' > /tmp/test.json
awslocal s3 cp /tmp/test.json s3://adelie-naver-reports/2026/02/16/test.json

# 파일 목록 확인
awslocal s3 ls s3://adelie-naver-reports/ --recursive

# 파일 다운로드
awslocal s3 cp s3://adelie-naver-reports/2026/02/16/test.json /tmp/downloaded.json

# 파일 삭제
awslocal s3 rm s3://adelie-naver-reports/2026/02/16/test.json

# 버킷 전체 삭제
awslocal s3 rb s3://adelie-naver-reports --force
```

### 4.3 Secrets Manager

```bash
# 시크릿 생성
awslocal secretsmanager create-secret \
  --name adelie/openai-api-key \
  --secret-string "sk-test-openai-key-for-localstack"

awslocal secretsmanager create-secret \
  --name adelie/jwt-secret \
  --secret-string "localstack-test-jwt-secret-32chars"

awslocal secretsmanager create-secret \
  --name adelie/perplexity-api-key \
  --secret-string "pplx-test-key"

awslocal secretsmanager create-secret \
  --name adelie/db-password \
  --secret-string "localstack-test-password"

# 시크릿 목록 확인
awslocal secretsmanager list-secrets

# 시크릿 값 조회
awslocal secretsmanager get-secret-value --secret-id adelie/openai-api-key

# 시크릿 값 업데이트
awslocal secretsmanager update-secret \
  --secret-id adelie/openai-api-key \
  --secret-string "sk-updated-test-key"

# 시크릿 삭제
awslocal secretsmanager delete-secret \
  --secret-id adelie/openai-api-key \
  --force-delete-without-recovery
```

### 4.4 CloudWatch Logs

```bash
# 로그 그룹 생성
awslocal logs create-log-group --log-group-name /ecs/adelie-frontend
awslocal logs create-log-group --log-group-name /ecs/adelie-backend-api
awslocal logs create-log-group --log-group-name /ecs/adelie-ai-pipeline

# 로그 그룹 목록
awslocal logs describe-log-groups --log-group-name-prefix /ecs/adelie

# 보존 기간 설정 (30일)
awslocal logs put-retention-policy \
  --log-group-name /ecs/adelie-backend-api \
  --retention-in-days 30

# 로그 스트림 생성 + 로그 전송 (테스트)
awslocal logs create-log-stream \
  --log-group-name /ecs/adelie-backend-api \
  --log-stream-name ecs/backend-api/test-stream

awslocal logs put-log-events \
  --log-group-name /ecs/adelie-backend-api \
  --log-stream-name ecs/backend-api/test-stream \
  --log-events timestamp=$(date +%s000),message="[INFO] API 서버 시작"

# 로그 조회
awslocal logs get-log-events \
  --log-group-name /ecs/adelie-backend-api \
  --log-stream-name ecs/backend-api/test-stream
```

### 4.5 IAM

```bash
# 역할 생성 테스트
awslocal iam create-role \
  --role-name adelie-ecs-execution-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 역할 목록
awslocal iam list-roles --query "Roles[?starts_with(RoleName, 'adelie')]"

# 정책 연결
awslocal iam attach-role-policy \
  --role-name adelie-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 역할 삭제
awslocal iam detach-role-policy \
  --role-name adelie-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
awslocal iam delete-role --role-name adelie-ecs-execution-role
```

### 4.6 RDS (주의: 제한사항 있음)

> **LocalStack 커뮤니티 에디션 제한사항**: RDS는 메타데이터(인스턴스 생성/조회)만 에뮬레이션됩니다. 실제 PostgreSQL 인스턴스가 생성되지는 않습니다. 실제 DB 연결이 필요한 테스트는 `docker-compose.dev.yml`의 PostgreSQL 컨테이너를 사용하세요.

```bash
# DB 인스턴스 생성 (메타데이터만)
awslocal rds create-db-instance \
  --db-instance-identifier adelie-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16 \
  --master-username narative \
  --master-user-password "test-password" \
  --db-name narrative_invest

# 인스턴스 조회
awslocal rds describe-db-instances --db-instance-identifier adelie-db

# 인스턴스 삭제
awslocal rds delete-db-instance \
  --db-instance-identifier adelie-db \
  --skip-final-snapshot
```

**대안**: 실제 DB 접속 테스트는 docker-compose.dev.yml의 PostgreSQL 사용

```bash
# 개발 환경 PostgreSQL 실행
make dev
# → localhost:5433에서 PostgreSQL 접속 가능
```

### 4.7 ElastiCache (주의: 제한사항 있음)

> **LocalStack 커뮤니티 에디션 제한사항**: ElastiCache도 메타데이터만 에뮬레이션됩니다. 실제 Redis 연결 테스트는 `docker-compose.dev.yml`의 Redis 컨테이너를 사용하세요.

```bash
# 서브넷 그룹 조회 (Terraform에서 생성)
awslocal elasticache describe-cache-subnet-groups

# 클러스터 조회
awslocal elasticache describe-cache-clusters
```

---

## 5. Makefile 명령어 요약

프로젝트 루트의 `Makefile`에 정의된 LocalStack + Terraform 관련 명령어:

| 명령어 | 설명 | 비고 |
|--------|------|------|
| `make localstack-up` | LocalStack 컨테이너 시작 | `localhost:4566`에서 서비스 제공 |
| `make localstack-down` | LocalStack 컨테이너 중지 | 볼륨 데이터는 보존됨 |
| `make terraform-init` | Terraform 초기화 | `ENV=localstack` (기본값) |
| `make terraform-plan` | Terraform 실행 계획 확인 | 변경사항 미리보기 |
| `make terraform-apply` | Terraform 적용 | `-auto-approve` 포함 |
| `make terraform-destroy` | Terraform 리소스 삭제 | `-auto-approve` 포함 |

### ENV 변수로 환경 전환

```bash
# LocalStack 대상 (기본값)
make terraform-init                  # ENV=localstack

# 실제 AWS dev 환경 대상
make terraform-init ENV=dev
make terraform-plan ENV=dev
make terraform-apply ENV=dev
```

### 일반적인 작업 흐름

```bash
# 1. LocalStack 시작
make localstack-up

# 2. Terraform으로 인프라 생성
make terraform-init
make terraform-plan
make terraform-apply

# 3. 서비스별 수동 테스트 (awslocal 사용)
awslocal s3 ls
awslocal ecr describe-repositories
awslocal secretsmanager list-secrets

# 4. Terraform 모듈 수정 후 재적용
make terraform-plan
make terraform-apply

# 5. 테스트 완료 후 정리
make terraform-destroy
make localstack-down
```

---

## 6. 트러블슈팅

### 6.1 Docker Socket 권한 오류

**증상**:
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**해결**:
```bash
# Docker 소켓 권한 확인
ls -la /var/run/docker.sock

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 그룹 변경 적용 (재로그인 또는)
newgrp docker

# 권한 직접 변경 (임시)
sudo chmod 666 /var/run/docker.sock
```

### 6.2 포트 충돌 (4566)

**증상**:
```
Bind for 0.0.0.0:4566 failed: port is already allocated
```

**해결**:
```bash
# 4566 포트를 사용 중인 프로세스 확인
sudo lsof -i :4566

# 해당 프로세스 종료
sudo kill -9 <PID>

# 또는 기존 LocalStack 컨테이너 확인 후 제거
docker ps -a | grep localstack
docker rm -f <container_id>

# LocalStack 재시작
make localstack-up
```

### 6.3 Persistence 데이터 초기화

**증상**: 이전 상태가 남아서 Terraform이 꼬이는 경우

**해결**:
```bash
# LocalStack 중지 + 볼륨 삭제
cd infra/localstack && docker compose down -v

# Terraform 상태 파일도 삭제
rm -f infra/terraform/environments/localstack/terraform.tfstate*

# 깨끗한 상태에서 재시작
make localstack-up
make terraform-init
make terraform-apply
```

### 6.4 Terraform init 실패

**증상**:
```
Error: Failed to get existing workspaces
```

**해결**:
```bash
# .terraform 디렉토리 삭제 후 재초기화
rm -rf infra/terraform/environments/localstack/.terraform
rm -f infra/terraform/environments/localstack/.terraform.lock.hcl
make terraform-init
```

### 6.5 LocalStack 메모리 부족

**증상**: LocalStack 컨테이너가 반복적으로 OOM 종료

**해결**:
```bash
# Docker 메모리 할당 확인
docker stats localstack

# docker-compose.yml에 메모리 제한 추가
# services:
#   localstack:
#     deploy:
#       resources:
#         limits:
#           memory: 4G
```

또는 불필요한 서비스를 `SERVICES` 환경변수에서 제거하여 메모리 사용량을 줄일 수 있습니다.

### 6.6 awslocal 명령어를 찾을 수 없음

**증상**:
```
command not found: awslocal
```

**해결**:
```bash
# awslocal 설치
pip install awscli-local

# 또는 aws CLI에 --endpoint-url을 직접 지정
aws --endpoint-url=http://localhost:4566 s3 ls

# alias 설정 (awslocal 미설치 시 대안)
alias awslocal='aws --endpoint-url=http://localhost:4566'
```

### 6.7 LocalStack Community vs Pro 기능 차이

LocalStack Community Edition(무료)에서 **지원되지 않거나 제한적인** 서비스:

| 서비스 | 지원 수준 | 비고 |
|--------|-----------|------|
| S3 | 완전 지원 | |
| Secrets Manager | 완전 지원 | |
| ECR | 완전 지원 | |
| IAM | 완전 지원 | |
| CloudWatch Logs | 완전 지원 | |
| ECS | 부분 지원 | 태스크 정의 등록 가능, 실제 컨테이너 실행은 Pro |
| RDS | 메타데이터만 | 실제 DB 인스턴스 생성 불가 |
| ElastiCache | 메타데이터만 | 실제 Redis 인스턴스 생성 불가 |
| ELB/ALB | 부분 지원 | 라우팅 규칙 등록 가능, 실제 트래픽 라우팅은 Pro |
| Route53 | 부분 지원 | 레코드 등록 가능, DNS 해석은 Pro |

> **권장**: RDS와 ElastiCache는 `docker-compose.dev.yml`의 PostgreSQL/Redis 컨테이너를 병행 사용하세요. LocalStack은 Terraform 모듈 검증과 ECR/S3/Secrets Manager 테스트에 집중합니다.

---

## 7. 참고 자료

- [LocalStack 공식 문서](https://docs.localstack.cloud/)
- [LocalStack GitHub](https://github.com/localstack/localstack)
- [awscli-local PyPI](https://pypi.org/project/awscli-local/)
- 프로젝트 내 관련 파일:
  - `infra/localstack/docker-compose.yml` — LocalStack 컨테이너 정의
  - `infra/terraform/environments/localstack/main.tf` — LocalStack Terraform 진입점
  - `infra/terraform/modules/` — 공통 Terraform 모듈
  - `Makefile` — localstack-up/down, terraform-init/plan/apply/destroy 명령어
