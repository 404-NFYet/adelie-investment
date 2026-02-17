# AWS IAM 권한 신청서 - Adelie Investment

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 서비스명 | Adelie Investment (AI 금융 교육 플랫폼) |
| AWS 리전 | ap-northeast-2 (서울) |
| 팀 규모 | 5명 (인프라 1, AI 개발 1, AI QA 1, 백엔드 1, 프론트엔드 1) |
| 예상 월 비용 | $200~300 (dev 환경 기준) |
| 사용 서비스 | ECS Fargate, ECR, RDS PostgreSQL, ElastiCache Redis, S3, Secrets Manager, CloudWatch, Route53, VPC |
| IaC 도구 | Terraform (S3 + DynamoDB 원격 상태 관리) |
| CI/CD | GitHub Actions (OIDC 인증) |

### 서비스 구성

```
사용자 → ALB → ECS Fargate (frontend, backend-api, ai-pipeline)
                  ├── RDS PostgreSQL 16 + pgvector
                  ├── ElastiCache Redis 7
                  ├── S3 (리포트 저장)
                  └── Secrets Manager (API 키 관리)
```

### ECR 리포지토리

- `adelie-frontend` — React 19 + Nginx SPA
- `adelie-backend-api` — FastAPI (인증, API, 챗봇 포함)
- `adelie-ai-pipeline` — LangGraph 데이터 파이프라인

---

## 2. IAM 역할 정의

### 2.1 TerraformExecutor — 인프라 관리자

| 항목 | 내용 |
|------|------|
| 역할명 | `adelie-terraform-executor` |
| 목적 | Terraform으로 AWS 인프라 생성/수정/삭제 |
| 담당자 | 도형준 (dorae222) |
| 신뢰 관계 | IAM 사용자 (콘솔/CLI 접속) |

#### Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:user/dorae222"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    }
  ]
}
```

#### IAM Policy — `adelie-terraform-executor-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2FullAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ECSFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ECRFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:*"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:*:repository/adelie-*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ECRAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "RDSFullAccess",
      "Effect": "Allow",
      "Action": [
        "rds:*"
      ],
      "Resource": "arn:aws:rds:ap-northeast-2:*:*:adelie-*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "RDSDescribe",
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBSubnetGroups",
        "rds:DescribeDBParameterGroups",
        "rds:DescribeOrderableDBInstanceOptions",
        "rds:DescribeEngineDefaultParameters"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ElastiCacheFullAccess",
      "Effect": "Allow",
      "Action": [
        "elasticache:*"
      ],
      "Resource": "arn:aws:elasticache:ap-northeast-2:*:*:adelie-*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ElastiCacheDescribe",
      "Effect": "Allow",
      "Action": [
        "elasticache:DescribeCacheClusters",
        "elasticache:DescribeCacheSubnetGroups",
        "elasticache:DescribeCacheParameterGroups",
        "elasticache:DescribeReplicationGroups"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "S3FullAccess",
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "arn:aws:s3:::adelie-*",
        "arn:aws:s3:::adelie-*/*"
      ]
    },
    {
      "Sid": "TerraformStateS3",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketVersioning",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::adelie-terraform-state*",
        "arn:aws:s3:::adelie-terraform-state*/*"
      ]
    },
    {
      "Sid": "TerraformStateDynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-2:*:table/adelie-terraform-lock"
    },
    {
      "Sid": "VPCFullAccess",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc",
        "ec2:DeleteVpc",
        "ec2:ModifyVpcAttribute",
        "ec2:DescribeVpcs",
        "ec2:CreateSubnet",
        "ec2:DeleteSubnet",
        "ec2:DescribeSubnets",
        "ec2:CreateInternetGateway",
        "ec2:DeleteInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:DetachInternetGateway",
        "ec2:CreateNatGateway",
        "ec2:DeleteNatGateway",
        "ec2:DescribeNatGateways",
        "ec2:AllocateAddress",
        "ec2:ReleaseAddress",
        "ec2:DescribeAddresses",
        "ec2:CreateRouteTable",
        "ec2:DeleteRouteTable",
        "ec2:CreateRoute",
        "ec2:DeleteRoute",
        "ec2:AssociateRouteTable",
        "ec2:DisassociateRouteTable",
        "ec2:DescribeRouteTables",
        "ec2:CreateSecurityGroup",
        "ec2:DeleteSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:DescribeSecurityGroups",
        "ec2:CreateTags",
        "ec2:DeleteTags",
        "ec2:DescribeTags",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeAccountAttributes",
        "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "IAMScopedAccess",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:GetRole",
        "iam:UpdateRole",
        "iam:PassRole",
        "iam:AttachRolePolicy",
        "iam:DetachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy",
        "iam:GetRolePolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "iam:ListInstanceProfilesForRole",
        "iam:CreateInstanceProfile",
        "iam:DeleteInstanceProfile",
        "iam:AddRoleToInstanceProfile",
        "iam:RemoveRoleFromInstanceProfile",
        "iam:TagRole",
        "iam:UntagRole"
      ],
      "Resource": "arn:aws:iam::*:role/adelie-*"
    },
    {
      "Sid": "IAMPolicyManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreatePolicy",
        "iam:DeletePolicy",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "iam:ListPolicyVersions",
        "iam:CreatePolicyVersion",
        "iam:DeletePolicyVersion"
      ],
      "Resource": "arn:aws:iam::*:policy/adelie-*"
    },
    {
      "Sid": "IAMServiceLinkedRole",
      "Effect": "Allow",
      "Action": [
        "iam:CreateServiceLinkedRole"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:AWSServiceName": [
            "ecs.amazonaws.com",
            "elasticache.amazonaws.com",
            "rds.amazonaws.com",
            "elasticloadbalancing.amazonaws.com"
          ]
        }
      }
    },
    {
      "Sid": "SecretsManagerFullAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:DeleteSecret",
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecret",
        "secretsmanager:TagResource",
        "secretsmanager:UntagResource",
        "secretsmanager:GetResourcePolicy",
        "secretsmanager:PutResourcePolicy",
        "secretsmanager:DeleteResourcePolicy",
        "secretsmanager:ListSecretVersionIds"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:adelie/*"
    },
    {
      "Sid": "SecretsManagerList",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:ListSecrets"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchFullAccess",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:DeleteLogGroup",
        "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy",
        "logs:DeleteRetentionPolicy",
        "logs:TagLogGroup",
        "logs:UntagLogGroup",
        "logs:ListTagsLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "cloudwatch:PutDashboard",
        "cloudwatch:DeleteDashboards",
        "cloudwatch:GetDashboard",
        "cloudwatch:ListDashboards"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "Route53Access",
      "Effect": "Allow",
      "Action": [
        "route53:GetHostedZone",
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets",
        "route53:ListResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ELBAccess",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "EventBridgeAccess",
      "Effect": "Allow",
      "Action": [
        "events:PutRule",
        "events:DeleteRule",
        "events:DescribeRule",
        "events:PutTargets",
        "events:RemoveTargets",
        "events:ListTargetsByRule",
        "events:ListRules",
        "events:TagResource",
        "events:UntagResource"
      ],
      "Resource": "arn:aws:events:ap-northeast-2:*:rule/adelie-*"
    },
    {
      "Sid": "STSAccess",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 2.2 ECSTaskExecution — 서비스 런타임

| 항목 | 내용 |
|------|------|
| 역할명 | `adelie-ecs-execution-role` |
| 목적 | ECS Fargate 태스크 실행 시 ECR 이미지 풀, 시크릿 조회, 로그 전송 |
| 사용 주체 | ECS 서비스 (ecs-tasks.amazonaws.com) |

#### Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

#### IAM Policy — `adelie-ecs-execution-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPullAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:*:repository/adelie-*"
    },
    {
      "Sid": "ECRAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:adelie/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:log-group:/ecs/adelie-*:*"
    },
    {
      "Sid": "CloudWatchLogGroup",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:log-group:*"
    }
  ]
}
```

#### 추가: ECS Task Role — `adelie-ecs-task-role`

애플리케이션 런타임에서 사용하는 역할 (S3 접근 등):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::adelie-*",
        "arn:aws:s3:::adelie-*/*"
      ]
    },
    {
      "Sid": "SecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:adelie/*"
    }
  ]
}
```

---

### 2.3 CICDPipeline — GitHub Actions

| 항목 | 내용 |
|------|------|
| 역할명 | `adelie-cicd-pipeline-role` |
| 목적 | GitHub Actions에서 ECR 이미지 푸시, ECS 서비스 업데이트 |
| 사용 주체 | GitHub Actions (OIDC — sts.amazonaws.com) |
| GitHub 리포지토리 | `dorae222/adelie-investment` |

#### Trust Policy — GitHub OIDC

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
          "token.actions.githubusercontent.com:sub": "repo:dorae222/adelie-investment:*"
        }
      }
    }
  ]
}
```

> **사전 설정**: AWS 계정에 GitHub OIDC Identity Provider가 등록되어 있어야 합니다.
> `arn:aws:iam::ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com`

#### IAM Policy — `adelie-cicd-pipeline-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRPushAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:ListImages",
        "ecr:DescribeImages"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:*:repository/adelie-*"
    },
    {
      "Sid": "ECRAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSServiceUpdate",
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:DeregisterTaskDefinition",
        "ecs:ListTasks",
        "ecs:DescribeTasks",
        "ecs:ListServices"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ECSPassRole",
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/adelie-ecs-execution-role",
        "arn:aws:iam::*:role/adelie-ecs-task-role"
      ]
    },
    {
      "Sid": "CloudWatchLogsRead",
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:DescribeLogStreams",
        "logs:DescribeLogGroups"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:log-group:/ecs/adelie-*:*"
    }
  ]
}
```

---

### 2.4 Developer — 팀원 개발용

| 항목 | 내용 |
|------|------|
| 역할명 | `adelie-developer-role` |
| 목적 | 개발자가 ECR 이미지 푸시/풀, S3 접근, 로그 조회, ECS 상태 확인에 사용 |
| 대상 | 4명 (손영진, 정지훈, 안례진, 허진서) |

#### Trust Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::ACCOUNT_ID:user/YJ99Son",
          "arn:aws:iam::ACCOUNT_ID:user/J2hoon10",
          "arn:aws:iam::ACCOUNT_ID:user/ryejinn",
          "arn:aws:iam::ACCOUNT_ID:user/jjjh02"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

#### IAM Policy — `adelie-developer-policy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRReadWrite",
      "Effect": "Allow",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:DescribeRepositories",
        "ecr:ListImages",
        "ecr:DescribeImages",
        "ecr:GetRepositoryPolicy",
        "ecr:ListTagsForResource"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-2:*:repository/adelie-*"
    },
    {
      "Sid": "ECRAuthToken",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::adelie-*",
        "arn:aws:s3:::adelie-*/*"
      ]
    },
    {
      "Sid": "CloudWatchLogsReadOnly",
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents",
        "logs:GetQueryResults",
        "logs:StartQuery",
        "logs:StopQuery"
      ],
      "Resource": "arn:aws:logs:ap-northeast-2:*:log-group:/ecs/adelie-*:*"
    },
    {
      "Sid": "ECSReadOnly",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTasks",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeClusters",
        "ecs:ListServices",
        "ecs:ListTasks",
        "ecs:ListTaskDefinitions",
        "ecs:ListClusters"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "SecretsManagerReadOnly",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets"
      ],
      "Resource": "arn:aws:secretsmanager:ap-northeast-2:*:secret:adelie/*"
    },
    {
      "Sid": "RDSReadOnly",
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters",
        "rds:DescribeDBSubnetGroups"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    },
    {
      "Sid": "ElastiCacheReadOnly",
      "Effect": "Allow",
      "Action": [
        "elasticache:DescribeCacheClusters",
        "elasticache:DescribeReplicationGroups",
        "elasticache:DescribeCacheSubnetGroups"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-northeast-2"
        }
      }
    }
  ]
}
```

---

## 3. 역할 배정 요약

| 역할 | IAM Role 이름 | 대상 | 주요 권한 |
|------|---------------|------|-----------|
| TerraformExecutor | `adelie-terraform-executor` | 도형준 | EC2, ECS, ECR, RDS, ElastiCache, S3, VPC, IAM, Secrets Manager, CloudWatch, Route53 전체 관리 |
| ECSTaskExecution | `adelie-ecs-execution-role` | ECS Fargate 서비스 | ECR Pull, Secrets Manager Read, CloudWatch Logs Write |
| ECS Task | `adelie-ecs-task-role` | ECS 컨테이너 애플리케이션 | S3 Read/Write, Secrets Manager Read |
| CICDPipeline | `adelie-cicd-pipeline-role` | GitHub Actions (OIDC) | ECR Push, ECS Service Update, PassRole |
| Developer | `adelie-developer-role` | 손영진, 정지훈, 안례진, 허진서 | ECR Read/Write, S3 Access, Logs Read, ECS Read |

## 4. 리소스 네이밍 규칙

모든 AWS 리소스는 `adelie-` 접두사를 사용하여 IAM 정책의 리소스 범위를 제한합니다.

| 리소스 유형 | 네이밍 패턴 | 예시 |
|-------------|-------------|------|
| ECR 리포지토리 | `adelie-{service}` | `adelie-frontend`, `adelie-backend-api`, `adelie-ai-pipeline` |
| ECS 클러스터 | `adelie-cluster` | — |
| ECS 서비스 | `adelie-{service}` | `adelie-frontend`, `adelie-backend-api` |
| RDS 인스턴스 | `adelie-db` | — |
| ElastiCache | `adelie-redis` | — |
| S3 버킷 | `adelie-{purpose}` | `adelie-naver-reports`, `adelie-extracted-data` |
| Secrets | `adelie/{key-name}` | `adelie/openai-api-key`, `adelie/jwt-secret` |
| CloudWatch 로그 | `/ecs/adelie-{service}` | `/ecs/adelie-frontend`, `/ecs/adelie-backend-api` |
| IAM 역할 | `adelie-{purpose}-role` | `adelie-ecs-execution-role` |
| Terraform State | `adelie-terraform-state` (S3) + `adelie-terraform-lock` (DynamoDB) | — |
| EventBridge 규칙 | `adelie-{schedule}` | `adelie-daily-pipeline` |

## 5. 보안 고려사항

1. **리전 잠금**: 모든 역할은 `ap-northeast-2` (서울) 리전으로 제한
2. **리소스 범위 제한**: `adelie-*` 접두사로 다른 프로젝트 리소스 접근 차단
3. **최소 권한 원칙**: Developer 역할은 Read 위주, 인프라 변경 권한 없음
4. **OIDC 인증**: GitHub Actions는 장기 자격 증명(Access Key) 대신 OIDC 토큰 사용
5. **Secrets Manager**: API 키는 환경변수가 아닌 Secrets Manager에서 런타임 주입
6. **Terraform State 분리**: 상태 파일은 별도 S3 버킷 + DynamoDB 잠금으로 관리
7. **IAM Role 범위**: Terraform이 생성하는 IAM 역할은 `adelie-*` 패턴으로 제한

## 6. 사전 필요 설정

AWS 계정 관리자가 아래 항목을 먼저 설정해야 합니다:

1. **Terraform State 백엔드 생성**
   ```bash
   # S3 버킷 (Terraform 상태 파일)
   aws s3api create-bucket \
     --bucket adelie-terraform-state \
     --region ap-northeast-2 \
     --create-bucket-configuration LocationConstraint=ap-northeast-2

   aws s3api put-bucket-versioning \
     --bucket adelie-terraform-state \
     --versioning-configuration Status=Enabled

   aws s3api put-bucket-encryption \
     --bucket adelie-terraform-state \
     --server-side-encryption-configuration '{
       "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
     }'

   # DynamoDB 테이블 (Terraform 잠금)
   aws dynamodb create-table \
     --table-name adelie-terraform-lock \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST \
     --region ap-northeast-2
   ```

2. **GitHub OIDC Provider 등록**
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
   ```

3. **IAM 사용자 생성** (각 팀원별 — 콘솔/CLI 접속용)
   - `dorae222` (도형준 — 인프라)
   - `YJ99Son` (손영진 — 프론트엔드)
   - `J2hoon10` (정지훈 — AI 개발)
   - `ryejinn` (안례진 — AI QA)
   - `jjjh02` (허진서 — 백엔드)
