# ============================================================
# Adelie - LocalStack 테스트 환경 Terraform 진입점
# 사용법: terraform init && terraform plan && terraform apply
# LocalStack이 localhost:4566에서 실행 중이어야 합니다
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # LocalStack은 로컬 상태 파일 사용
  backend "local" {
    path = "terraform.tfstate"
  }
}

# --- LocalStack 전용 provider ---
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

  default_tags {
    tags = {
      Project     = "adelie-investment"
      Environment = "localstack"
      ManagedBy   = "terraform"
    }
  }
}

# --- VPC ---
module "vpc" {
  source = "../../modules/vpc"

  vpc_cidr        = "10.0.0.0/16"
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = ["10.0.10.0/24", "10.0.20.0/24"]
  azs             = ["ap-northeast-2a", "ap-northeast-2c"]
  project_name    = "adelie"
}

# --- Bastion ---
module "bastion" {
  source = "../../modules/bastion"

  vpc_id           = module.vpc.vpc_id
  public_subnet_id = module.vpc.public_subnet_ids[0]
  key_name         = "adelie-localstack-key"
  allowed_ssh_cidr = "0.0.0.0/0"
  project_name     = "adelie"
}

# --- ECR ---
module "ecr" {
  source = "../../modules/ecr"

  project_name = "adelie"
  services     = ["frontend", "backend-api", "ai-pipeline"]
}

# --- RDS (PostgreSQL + pgvector) ---
module "rds" {
  source = "../../modules/rds"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = "narrative_invest"
  db_username        = "narative"
  db_password        = "localstack-test-password"
  instance_class     = "db.t3.micro"
  project_name       = "adelie"
}

# --- ElastiCache (Redis) ---
module "elasticache" {
  source = "../../modules/elasticache"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type          = "cache.t3.micro"
  project_name       = "adelie"
}

# --- S3 (MinIO 대체) ---
module "s3" {
  source = "../../modules/s3"

  project_name = "adelie"
  buckets      = ["naver-reports", "extracted-data"]
}

# --- Secrets Manager ---
module "secrets" {
  source = "../../modules/secrets"

  project_name = "adelie"
  secrets = {
    "openai-api-key"     = "test-openai-key"
    "perplexity-api-key" = "test-perplexity-key"
    "claude-api-key"     = "test-claude-key"
    "kis-app-key"        = "test-kis-key"
    "kis-app-secret"     = "test-kis-secret"
    "db-password"        = "localstack-test-password"
    "jwt-secret"         = "localstack-test-jwt-secret-32chars"
  }
}

# --- ECS Fargate ---
module "ecs" {
  source = "../../modules/ecs"

  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  ecr_urls           = module.ecr.repository_urls
  rds_endpoint       = module.rds.endpoint
  redis_endpoint     = module.elasticache.endpoint
  secrets_arns       = module.secrets.secret_arns
  project_name       = "adelie"
}

# --- 출력값 ---
output "alb_url" {
  description = "Application Load Balancer URL"
  value       = module.ecs.alb_dns_name
}

output "bastion_ip" {
  description = "Bastion Host Public IP"
  value       = module.bastion.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL Endpoint"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis Endpoint"
  value       = module.elasticache.endpoint
}

output "ecr_urls" {
  description = "ECR Repository URLs"
  value       = module.ecr.repository_urls
}

output "s3_buckets" {
  description = "S3 Bucket Names"
  value       = module.s3.bucket_names
}
