variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "프라이빗 서브넷 ID 목록"
  type        = list(string)
}

variable "node_type" {
  description = "ElastiCache 노드 타입"
  type        = string
  default     = "cache.t3.micro"
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}
