/**
 * staging 환경
 * 저비용: Fargate Spot, 단일 AZ RDS, cache.t4g.micro
 * 목표 비용: ~$50/월
 */

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 원격 상태 파일 (S3 + DynamoDB 잠금)
  # 초기 설정 후 주석 해제
  # backend "s3" {
  #   bucket         = "adelie-terraform-state"
  #   key            = "staging/terraform.tfstate"
  #   region         = "ap-northeast-2"
  #   dynamodb_table = "adelie-terraform-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = "ap-northeast-2"
}

locals {
  project     = "adelie"
  environment = "staging"
}

module "network" {
  source = "../../modules/network"

  project_name       = local.project
  environment        = local.environment
  vpc_cidr           = "10.1.0.0/16"
  availability_zones = ["ap-northeast-2a", "ap-northeast-2b"]
}

module "storage" {
  source = "../../modules/storage"

  project_name = local.project
  environment  = local.environment
  domain_name  = "adelie-invest.com"
}

module "database" {
  source = "../../modules/database"

  project_name            = local.project
  environment             = local.environment
  private_subnet_ids      = module.network.private_subnet_ids
  rds_security_group_id   = module.network.rds_security_group_id
  redis_security_group_id = module.network.redis_security_group_id

  db_instance_class    = "db.t3.micro"   # staging 저비용
  db_allocated_storage = 20
  db_name              = "narrative_invest"
  db_username          = "narative"
  db_password          = var.db_password

  redis_node_type = "cache.t4g.micro"
}

module "compute" {
  source = "../../modules/compute"

  project_name          = local.project
  environment           = local.environment
  vpc_id                = module.network.vpc_id
  public_subnet_ids     = module.network.public_subnet_ids
  private_subnet_ids    = module.network.private_subnet_ids
  alb_security_group_id = module.network.alb_security_group_id
  ecs_security_group_id = module.network.ecs_security_group_id
  ecr_repository_url    = module.storage.ecr_repository_url
  ecr_image_tag         = var.ecr_image_tag

  backend_cpu           = 256   # 0.25 vCPU
  backend_memory        = 512   # 512 MiB
  backend_desired_count = 1

  acm_certificate_arn = var.acm_certificate_arn
  secrets_arn         = var.secrets_arn
}

module "cdn" {
  source = "../../modules/cdn"

  project_name                    = local.project
  environment                     = local.environment
  frontend_bucket_name            = module.storage.frontend_bucket_name
  frontend_bucket_arn             = module.storage.frontend_bucket_arn
  frontend_bucket_regional_domain = "${module.storage.frontend_bucket_name}.s3.ap-northeast-2.amazonaws.com"
  acm_certificate_arn             = var.acm_certificate_arn
  domain_aliases                  = ["staging.adelie-invest.com"]
}

variable "db_password"          { type = string; sensitive = true }
variable "acm_certificate_arn"  { type = string }
variable "secrets_arn"          { type = string }
variable "ecr_image_tag"        { type = string; default = "latest" }
