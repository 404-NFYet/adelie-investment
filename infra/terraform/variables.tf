variable "project_name" {
  description = "프로젝트 이름 (리소스 태그 및 이름 접두사)"
  type        = string
  default     = "adelie"
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2" # 서울
}

variable "environment" {
  description = "배포 환경 (staging | prod)"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment는 'staging' 또는 'prod'이어야 합니다."
  }
}

# ── 네트워크 ──
variable "vpc_cidr" {
  description = "VPC CIDR 블록"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "사용할 가용 영역 목록"
  type        = list(string)
  default     = ["ap-northeast-2a", "ap-northeast-2b"]
}

# ── 컴퓨트 (ECS Fargate) ──
variable "backend_cpu" {
  description = "ECS Task CPU 단위 (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "ECS Task 메모리 (MiB)"
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "ECS Service 원하는 태스크 수"
  type        = number
  default     = 1
}

variable "ecr_image_tag" {
  description = "ECR 이미지 태그 (배포 시 override)"
  type        = string
  default     = "latest"
}

# ── 데이터베이스 ──
variable "db_instance_class" {
  description = "RDS 인스턴스 유형"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS 스토리지 크기 (GiB)"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "PostgreSQL 데이터베이스 이름"
  type        = string
  default     = "narrative_invest"
}

variable "db_username" {
  description = "PostgreSQL 사용자 이름"
  type        = string
  default     = "narative"
}

variable "db_password" {
  description = "PostgreSQL 비밀번호 (Secrets Manager 권장)"
  type        = string
  sensitive   = true
}

# ── Redis (ElastiCache) ──
variable "redis_node_type" {
  description = "ElastiCache Redis 노드 유형"
  type        = string
  default     = "cache.t4g.micro"
}

# ── 도메인 ──
variable "domain_name" {
  description = "서비스 도메인 (Route53 호스팅 영역)"
  type        = string
  default     = "adelie-invest.com"
}
