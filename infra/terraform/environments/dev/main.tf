# ============================================================
# Adelie - Dev 환경 Terraform 진입점
# 사용법: terraform init && terraform plan && terraform apply
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state (S3)
  backend "s3" {
    bucket         = "adelie-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-2"
    encrypt        = true
    dynamodb_table = "adelie-terraform-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "adelie-investment"
      Environment = "dev"
      ManagedBy   = "terraform"
    }
  }
}

# --- VPC ---
module "vpc" {
  source = "../../modules/vpc"

  vpc_cidr        = var.vpc_cidr
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets
  azs             = var.azs
  project_name    = var.project_name
}

# --- Bastion ---
module "bastion" {
  source = "../../modules/bastion"

  vpc_id           = module.vpc.vpc_id
  public_subnet_id = module.vpc.public_subnet_ids[0]
  key_name         = var.bastion_key_name
  allowed_ssh_cidr = var.allowed_ssh_cidr
  project_name     = var.project_name
}

# --- ECR ---
module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name
  services     = ["frontend", "backend-api", "backend-spring", "ai-pipeline"]
}

# --- RDS (PostgreSQL + pgvector) ---
module "rds" {
  source = "../../modules/rds"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  db_name            = var.db_name
  db_username        = var.db_username
  db_password        = var.db_password
  instance_class     = "db.t3.micro"
  project_name       = var.project_name
}

# --- ElastiCache (Redis) ---
module "elasticache" {
  source = "../../modules/elasticache"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  node_type          = "cache.t3.micro"
  project_name       = var.project_name
}

# --- S3 (MinIO 대체) ---
module "s3" {
  source = "../../modules/s3"

  project_name = var.project_name
  buckets      = ["naver-reports", "extracted-data"]
}

# --- Secrets Manager ---
module "secrets" {
  source = "../../modules/secrets"

  project_name = var.project_name
  secrets = {
    "openai-api-key"     = var.openai_api_key
    "perplexity-api-key" = var.perplexity_api_key
    "claude-api-key"     = var.claude_api_key
    "kis-app-key"        = var.kis_app_key
    "kis-app-secret"     = var.kis_app_secret
    "db-password"        = var.db_password
    "jwt-secret"         = var.jwt_secret
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
  project_name       = var.project_name
}
