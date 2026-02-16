variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "ALB용 퍼블릭 서브넷 ID 목록"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "ECS 태스크용 프라이빗 서브넷 ID 목록"
  type        = list(string)
}

variable "ecr_urls" {
  description = "ECR 레포지토리 URL 맵 (서비스명 → URL)"
  type        = map(string)
}

variable "rds_endpoint" {
  description = "RDS 엔드포인트 (호스트명)"
  type        = string
}

variable "redis_endpoint" {
  description = "ElastiCache Redis 엔드포인트 (호스트명)"
  type        = string
}

variable "secrets_arns" {
  description = "Secrets Manager ARN 맵 (키명 → ARN)"
  type        = map(string)
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}
