# Adelie Investment — AWS Terraform 인프라

현재 LXD 베어메탈 환경에서 AWS로 이전하기 위한 Terraform IaC.

## 아키텍처

```
CloudFront (CDN) ──→ S3 (frontend SPA)
ALB (HTTPS) ──→ ECS Fargate (FastAPI :8082)
                      ├─→ RDS PostgreSQL 15
                      └─→ ElastiCache Redis 7
```

## 디렉토리 구조

```
infra/terraform/
├── modules/
│   ├── network/    # VPC, 서브넷, NAT GW, 보안 그룹
│   ├── compute/    # ECS Cluster, Task Def, Service, ALB
│   ├── database/   # RDS PostgreSQL, ElastiCache Redis
│   ├── storage/    # S3 (frontend + media), ECR
│   └── cdn/        # CloudFront + S3 OAC
├── environments/
│   ├── staging/    # 저비용 (0.25vCPU, 단일 AZ, Fargate Spot)
│   └── prod/       # 고가용성 (0.5vCPU×2, Multi-AZ RDS)
├── variables.tf    # 공통 변수 정의
└── outputs.tf      # 공통 출력 정의
```

## 마이그레이션 단계

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | Terraform 상태 파일 초기화, VPC 구성 | 🔲 준비 중 |
| 2 | ECR 레포 생성, CI/CD GitHub Actions 구성 | 🔲 |
| 3 | staging AWS 구성, 병렬 운영 검증 (2주) | 🔲 |
| 4 | RDS/ElastiCache 데이터 마이그레이션 | 🔲 |
| 5 | DNS 전환 (Cloudflare → Route53) | 🔲 |
| 6 | LXD 인프라 정리 | 🔲 |

## 사전 요구사항

```bash
# Terraform 설치 (>= 1.6)
brew install terraform   # macOS
# 또는
apt-get install terraform  # Debian/Ubuntu

# AWS CLI 설정
aws configure
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY 필요
```

## Phase 1: 상태 파일 S3 버킷 초기화

```bash
# 상태 파일 저장용 S3 버킷 생성 (1회)
aws s3api create-bucket \
  --bucket adelie-terraform-state \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

aws s3api put-bucket-versioning \
  --bucket adelie-terraform-state \
  --versioning-configuration Status=Enabled

# DynamoDB 잠금 테이블 생성 (1회)
aws dynamodb create-table \
  --table-name adelie-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2
```

## staging 배포

```bash
cd infra/terraform/environments/staging

# backend 블록 주석 해제 후:
terraform init

terraform plan \
  -var="db_password=${DB_PASSWORD}" \
  -var="acm_certificate_arn=arn:aws:acm:ap-northeast-2:..." \
  -var="secrets_arn=arn:aws:secretsmanager:ap-northeast-2:..."

terraform apply
```

## 비용 예상 (프로덕션)

| 서비스 | 스펙 | 월 비용 (USD) |
|--------|------|-------------|
| ECS Fargate | 0.5vCPU/1GB × 2 | ~$15 |
| RDS PostgreSQL | db.t3.medium, 20GB | ~$40 |
| ElastiCache Redis | cache.t4g.micro | ~$12 |
| S3 + CloudFront | 정적 파일 + CDN | ~$5 |
| ALB | 1개 | ~$20 |
| NAT Gateway | 1개 | ~$35 |
| **합계** | | **~$130/월** |

> staging: Fargate Spot + 단일 AZ → **~$50/월**

## CI/CD

`.github/workflows/deploy-aws.yml` 참조.
Phase 5 완료 전까지는 `workflow_dispatch` (수동) 트리거만 사용.
