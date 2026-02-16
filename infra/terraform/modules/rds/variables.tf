variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "프라이빗 서브넷 ID 목록"
  type        = list(string)
}

variable "db_name" {
  description = "데이터베이스 이름"
  type        = string
  default     = "narrative_invest"
}

variable "db_username" {
  description = "데이터베이스 사용자명"
  type        = string
  default     = "narative"
}

variable "db_password" {
  description = "데이터베이스 비밀번호"
  type        = string
  sensitive   = true
}

variable "instance_class" {
  description = "RDS 인스턴스 타입"
  type        = string
  default     = "db.t3.micro"
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}
