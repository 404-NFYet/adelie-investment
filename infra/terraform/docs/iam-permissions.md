# AWS IAM 권한 요청서 — Adelie Investment AWS 이전

> **문서 목적**: AWS 계정 관리자(Admin)에게 제출하는 IAM 엔티티 생성 요청서.
> 모든 작업은 AWS CLI 기반으로 수행하며, 콘솔 의존 없이 완전 자동화를 목표로 함.
>
> - 리전: `ap-northeast-2` (서울)
> - GitHub 조직: `404-NFYet/adelie-investment`
> - Terraform 상태 버킷: `adelie-terraform-state`
> - 프로젝트 태그: `Project=adelie`, `ManagedBy=terraform`

---

## 아키텍처 개요

```
                        ┌─────────────────────────────────────────────┐
인터넷 사용자             │              AWS ap-northeast-2              │
    │                   │                                             │
    ▼                   │   ┌──────────────┐   ┌─────────────────┐   │
Cloudflare DNS  ──────►│   │  CloudFront  │   │   ALB (HTTPS)   │   │
(또는 Route53)          │   │  (Frontend)  │   │  (Backend API)  │   │
                        │   └──────┬───────┘   └────────┬────────┘   │
                        │          │                     │            │
                        │   ┌──────▼───────┐   ┌────────▼────────┐   │
                        │   │ S3 (SPA 정적) │   │  ECS Fargate    │   │
                        │   │  adelie-*-   │   │  (FastAPI:8082) │   │
                        │   │  frontend    │   └──┬──────┬───────┘   │
                        │   └──────────────┘      │      │           │
                        │                  ┌──────▼──┐ ┌─▼────────┐  │
                        │                  │   RDS   │ │ElastiCache│  │
                        │                  │PostgreSQL│ │  Redis 7  │  │
                        │                  │    15   │ │           │  │
                        │                  └─────────┘ └──────────┘  │
                        │                                             │
                        │   ┌──────────────┐   ┌─────────────────┐   │
                        │   │  S3 (Media)  │   │ Secrets Manager │   │
                        │   │  (MinIO 대체)│   │ (API Keys, DB)  │   │
                        │   └──────────────┘   └─────────────────┘   │
                        │                                             │
                        │   ┌──────────────┐   ┌─────────────────┐   │
                        │   │    ECR       │   │  CloudWatch     │   │
                        │   │ (Docker 이미지)│   │  Logs/Metrics   │   │
                        │   └──────────────┘   └─────────────────┘   │
                        └─────────────────────────────────────────────┘

CI/CD: GitHub Actions → (OIDC) → ECR push → ECS rolling deploy
```

---

## 사전 준비 (Admin 직접 수행 — Terraform 외부)

Terraform 상태 저장소는 Terraform으로 관리 불가(닭-달걀 문제).
아래 2개를 Admin이 AWS CLI로 먼저 생성:

```bash
# 1. Terraform 상태 S3 버킷 (버전관리 + 암호화 + 퍼블릭 차단)
aws s3api create-bucket \
  --bucket adelie-terraform-state \
  --region ap-northeast-2 \
  --create-bucket-configuration LocationConstraint=ap-northeast-2

aws s3api put-bucket-versioning \
  --bucket adelie-terraform-state \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket adelie-terraform-state \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block \
  --bucket adelie-terraform-state \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# 2. Terraform 락 DynamoDB 테이블
aws dynamodb create-table \
  --table-name adelie-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2 \
  --tags Key=Project,Value=adelie Key=ManagedBy,Value=terraform
```

---

## IAM 엔티티 1: Terraform 운영자 (로컬 CLI 실행용)

**엔티티 유형**: IAM User → Access Key 발급 (로컬 `aws configure` 용)
**User 이름**: `adelie-terraform-operator`
**목적**: 로컬에서 `terraform plan/apply` 실행, 인프라 전체 관리

### 생성 명령 (Admin 수행)

```bash
# User 생성
aws iam create-user \
  --user-name adelie-terraform-operator \
  --tags Key=Project,Value=adelie Key=Purpose,Value=terraform

# Access Key 발급 (출력값을 dorae222에게 전달)
aws iam create-access-key --user-name adelie-terraform-operator
```

### 부착할 정책: AdministratorAccess (권장)

**이유**: Terraform은 VPC, IAM Role, RDS, ECS, CloudFront 등 AWS 거의 전 서비스를
생성/수정/삭제한다. 세분화된 정책으로 시작하면 `terraform apply` 때마다
권한 오류로 막혀 개발 속도가 심각하게 저하된다.
초기 단계에서는 `AdministratorAccess`를 부여하고,
인프라가 안정화된 후 최소 권한으로 축소하는 것이 현실적이다.

```bash
# AdministratorAccess 부착 (가장 실용적)
aws iam attach-user-policy \
  --user-name adelie-terraform-operator \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

#### 대안: 세분화된 정책 (Admin이 최소 권한 원칙을 고수할 경우)

아래 관리형 정책들을 모두 부착:

```bash
POLICIES=(
  "arn:aws:iam::aws:policy/AmazonVPCFullAccess"
  "arn:aws:iam::aws:policy/AmazonECS_FullAccess"
  "arn:aws:iam::aws:policy/AmazonRDSFullAccess"
  "arn:aws:iam::aws:policy/AmazonElastiCacheFullAccess"
  "arn:aws:iam::aws:policy/AmazonS3FullAccess"
  "arn:aws:iam::aws:policy/CloudFrontFullAccess"
  "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess"
  "arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess"
  "arn:aws:iam::aws:policy/AWSCertificateManagerFullAccess"
  "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
  "arn:aws:iam::aws:policy/CloudWatchFullAccess"
  "arn:aws:iam::aws:policy/AmazonRoute53FullAccess"
  "arn:aws:iam::aws:policy/IAMFullAccess"
)

for policy in "${POLICIES[@]}"; do
  aws iam attach-user-policy \
    --user-name adelie-terraform-operator \
    --policy-arn "$policy"
done
```

그리고 아래 Custom Inline Policy 추가 (Terraform state + EC2 네트워킹 보완):

```bash
aws iam put-user-policy \
  --user-name adelie-terraform-operator \
  --policy-name adelie-terraform-custom \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "TerraformStateS3",
        "Effect": "Allow",
        "Action": [
          "s3:GetObject","s3:PutObject","s3:DeleteObject",
          "s3:ListBucket","s3:GetBucketVersioning","s3:GetEncryptionConfiguration"
        ],
        "Resource": [
          "arn:aws:s3:::adelie-terraform-state",
          "arn:aws:s3:::adelie-terraform-state/*"
        ]
      },
      {
        "Sid": "TerraformStateLock",
        "Effect": "Allow",
        "Action": [
          "dynamodb:GetItem","dynamodb:PutItem",
          "dynamodb:DeleteItem","dynamodb:DescribeTable"
        ],
        "Resource": "arn:aws:dynamodb:ap-northeast-2:*:table/adelie-terraform-lock"
      },
      {
        "Sid": "EC2Full",
        "Effect": "Allow",
        "Action": [
          "ec2:*",
          "elasticloadbalancing:*"
        ],
        "Resource": "*"
      },
      {
        "Sid": "ACMFull",
        "Effect": "Allow",
        "Action": ["acm:*"],
        "Resource": "*"
      },
      {
        "Sid": "IAMForECSRoles",
        "Effect": "Allow",
        "Action": [
          "iam:CreateRole","iam:DeleteRole","iam:GetRole",
          "iam:ListRoles","iam:PutRolePolicy","iam:DeleteRolePolicy",
          "iam:AttachRolePolicy","iam:DetachRolePolicy",
          "iam:ListAttachedRolePolicies","iam:ListRolePolicies",
          "iam:GetRolePolicy","iam:PassRole",
          "iam:CreateInstanceProfile","iam:DeleteInstanceProfile",
          "iam:AddRoleToInstanceProfile","iam:RemoveRoleFromInstanceProfile",
          "iam:TagRole","iam:UntagRole"
        ],
        "Resource": "*"
      },
      {
        "Sid": "OIDCProvider",
        "Effect": "Allow",
        "Action": [
          "iam:CreateOpenIDConnectProvider",
          "iam:DeleteOpenIDConnectProvider",
          "iam:GetOpenIDConnectProvider",
          "iam:ListOpenIDConnectProviders"
        ],
        "Resource": "*"
      },
      {
        "Sid": "STSAssumeRole",
        "Effect": "Allow",
        "Action": ["sts:AssumeRole","sts:GetCallerIdentity"],
        "Resource": "*"
      }
    ]
  }'
```

### dorae222 로컬 설정

```bash
# Access Key 설정 (Admin에게 받은 키)
aws configure --profile adelie
# AWS Access Key ID: AKIA...
# AWS Secret Access Key: ...
# Default region: ap-northeast-2
# Default output format: json

export AWS_PROFILE=adelie

# 설정 검증
aws sts get-caller-identity
```

---

## IAM 엔티티 2: GitHub Actions OIDC Role (CI/CD)

**현재 문제**: `deploy-aws.yml`이 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` 시크릿을 사용 중.
Access Key 방식은 만료/노출 위험이 있으며, OIDC 방식이 AWS 권고 표준.

**Role 이름**: `adelie-github-actions`

### 2-1. OIDC Provider 등록 (Admin, 1회)

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --client-id-list sts.amazonaws.com \
  --tags Key=Project,Value=adelie
```

### 2-2. Trust Policy 파일 생성 + Role 생성

```bash
# Trust Policy (404-NFYet/adelie-investment 레포만 허용)
cat > /tmp/github-actions-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub":
          "repo:404-NFYet/adelie-investment:*"
      }
    }
  }]
}
EOF

# Role 생성 (ACCOUNT_ID 교체 필요)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i "s/ACCOUNT_ID/$ACCOUNT_ID/g" /tmp/github-actions-trust.json

aws iam create-role \
  --role-name adelie-github-actions \
  --assume-role-policy-document file:///tmp/github-actions-trust.json \
  --tags Key=Project,Value=adelie Key=Purpose,Value=ci-cd
```

### 2-3. Permission Policy 부착

```bash
cat > /tmp/github-actions-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": ["ecr:GetAuthorizationToken"],
      "Resource": "*"
    },
    {
      "Sid": "ECRPush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:*:repository/adelie/*"
    },
    {
      "Sid": "ECSDeployBackend",
      "Effect": "Allow",
      "Action": [
        "ecs:RegisterTaskDefinition",
        "ecs:DescribeTaskDefinition",
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:ListServices",
        "ecs:DescribeClusters"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassExecutionRole",
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": "arn:aws:iam::*:role/adelie-*-ecs-execution-role",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "ecs-tasks.amazonaws.com"
        }
      }
    },
    {
      "Sid": "S3FrontendDeploy",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject","s3:GetObject","s3:DeleteObject",
        "s3:ListBucket","s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::adelie-*-frontend",
        "arn:aws:s3:::adelie-*-frontend/*"
      ]
    },
    {
      "Sid": "CloudFrontInvalidate",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetDistribution",
        "cloudfront:ListDistributions"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name adelie-github-actions \
  --policy-name adelie-github-actions-policy \
  --policy-document file:///tmp/github-actions-policy.json
```

### 2-4. deploy-aws.yml 수정 (Access Key → OIDC)

```yaml
# .github/workflows/deploy-aws.yml 수정 필요
permissions:
  id-token: write   # OIDC 필수
  contents: read

- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
    aws-region: ap-northeast-2
    # AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 제거
```

### 2-5. GitHub Secrets 등록 (CLI)

```bash
# gh CLI 사용
gh secret set AWS_ACCOUNT_ID --body "$(aws sts get-caller-identity --query Account --output text)"
gh secret set AWS_REGION --body "ap-northeast-2"
gh secret set AWS_ROLE_ARN --body "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/adelie-github-actions"
gh secret set DISCORD_WEBHOOK --body "https://discord.com/api/webhooks/..."

# Access Key 시크릿 삭제 (OIDC 전환 후)
gh secret delete AWS_ACCESS_KEY_ID
gh secret delete AWS_SECRET_ACCESS_KEY
```

---

## IAM 엔티티 3: ECS Task Execution Role (Terraform 자동 생성)

**Role 이름**: `adelie-{env}-ecs-execution-role`
**신뢰 관계**: `ecs-tasks.amazonaws.com`
**생성 주체**: Terraform compute 모듈이 자동 생성 (`iam:CreateRole` 권한 필요)

> ℹ️ dorae222가 직접 생성하지 않아도 됨.
> `adelie-terraform-operator`에 IAM 관련 권한이 있으면 Terraform이 생성.

자동 부착 정책:
- `AmazonECSTaskExecutionRolePolicy` (ECR pull, CloudWatch Logs)
- Inline: `secretsmanager:GetSecretValue` → `adelie-*` 시크릿

---

## IAM 엔티티 4: ECS Task Role (Terraform 자동 생성)

**Role 이름**: `adelie-{env}-ecs-task-role`
**용도**: FastAPI 컨테이너가 S3(미디어), CloudWatch, Secrets Manager에 접근

자동 부착 인라인 정책:
```json
{
  "S3MediaAccess": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"]
    → "arn:aws:s3:::adelie-{env}-media/*",
  "CloudWatchLogs": ["logs:CreateLogStream","logs:PutLogEvents"]
    → "/ecs/adelie-*",
  "CloudWatchMetrics": ["cloudwatch:PutMetricData"] → "*"
}
```

---

## ACM 인증서 요청 (CLI)

```bash
# us-east-1 (CloudFront용) + ap-northeast-2 (ALB용) 각각 필요
aws acm request-certificate \
  --domain-name "*.adelie-invest.com" \
  --subject-alternative-names "adelie-invest.com" \
  --validation-method DNS \
  --region ap-northeast-2 \
  --tags Key=Project,Value=adelie

# CloudFront는 반드시 us-east-1 인증서
aws acm request-certificate \
  --domain-name "*.adelie-invest.com" \
  --subject-alternative-names "adelie-invest.com" \
  --validation-method DNS \
  --region us-east-1 \
  --tags Key=Project,Value=adelie

# 인증서 ARN 조회
aws acm list-certificates --region ap-northeast-2 --query 'CertificateSummaryList[*].[CertificateArn,DomainName]' --output table
aws acm list-certificates --region us-east-1 --query 'CertificateSummaryList[*].[CertificateArn,DomainName]' --output table
```

---

## Secrets Manager 시크릿 생성 (dorae222)

```bash
# Staging
aws secretsmanager create-secret \
  --name "adelie-staging" \
  --region ap-northeast-2 \
  --tags Key=Project,Value=adelie Key=Env,Value=staging \
  --secret-string '{
    "DATABASE_URL":"postgresql+asyncpg://narative:PASSWORD@RDS_ENDPOINT:5432/narrative_invest",
    "REDIS_URL":"redis://REDIS_ENDPOINT:6379",
    "OPENAI_API_KEY":"sk-...",
    "PERPLEXITY_API_KEY":"pplx-...",
    "LANGCHAIN_API_KEY":"ls__...",
    "SECRET_KEY":"jwt-secret-min-32-chars",
    "DISCORD_PIPELINE_WEBHOOK":"https://discord.com/api/webhooks/..."
  }'

# Prod (별도)
aws secretsmanager create-secret \
  --name "adelie-prod" \
  --region ap-northeast-2 \
  --tags Key=Project,Value=adelie Key=Env,Value=prod \
  --secret-string '{ ... }'
```

---

## Terraform 첫 실행 순서 (CLI 전체)

```bash
# 1. 자격증명 확인
export AWS_PROFILE=adelie
aws sts get-caller-identity

# 2. S3 상태 백엔드 활성화 (environments/staging/main.tf의 backend 블록 주석 해제)
cd infra/terraform/environments/staging
# main.tf에서 backend "s3" { ... } 주석 해제

# 3. 초기화
terraform init \
  -backend-config="bucket=adelie-terraform-state" \
  -backend-config="key=staging/terraform.tfstate" \
  -backend-config="dynamodb_table=adelie-terraform-lock" \
  -backend-config="region=ap-northeast-2"

# 4. Plan (필수 변수 지정)
SECRETS_ARN=$(aws secretsmanager describe-secret \
  --secret-id adelie-staging \
  --query ARN --output text)

ACM_ARN_SEOUL=$(aws acm list-certificates \
  --region ap-northeast-2 \
  --query 'CertificateSummaryList[0].CertificateArn' \
  --output text)

terraform plan \
  -var="db_password=$DB_PASS" \
  -var="acm_certificate_arn=$ACM_ARN_SEOUL" \
  -var="secrets_arn=$SECRETS_ARN" \
  -out=tfplan

# 5. Apply
terraform apply tfplan

# 6. 결과 확인
terraform output
```

---

## 권한 요청 체크리스트 (Admin 검토용)

| # | 항목 | 수행자 | 완료 |
|---|------|--------|------|
| 1 | S3 버킷 `adelie-terraform-state` 생성 (버전관리, 암호화, 퍼블릭차단) | Admin | ☐ |
| 2 | DynamoDB 테이블 `adelie-terraform-lock` 생성 | Admin | ☐ |
| 3 | IAM User `adelie-terraform-operator` 생성 + AdministratorAccess 부착 | Admin | ☐ |
| 4 | Access Key 발급 → dorae222에게 전달 | Admin | ☐ |
| 5 | GitHub Actions OIDC Provider 등록 | Admin | ☐ |
| 6 | IAM Role `adelie-github-actions` 생성 + Trust + Permission | Admin/dorae222 | ☐ |
| 7 | ACM 인증서 요청 (ap-northeast-2 + us-east-1 각 1개) | dorae222 | ☐ |
| 8 | Secrets Manager `adelie-staging` / `adelie-prod` 생성 | dorae222 | ☐ |
| 9 | GitHub Secrets 등록 (AWS_ACCOUNT_ID, AWS_ROLE_ARN 등) | dorae222 | ☐ |
| 10 | `terraform init && terraform plan` 검증 (staging) | dorae222 | ☐ |
| 11 | `terraform apply` staging 환경 | dorae222 | ☐ |
