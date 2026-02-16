variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_id" {
  description = "Bastion을 배치할 퍼블릭 서브넷 ID"
  type        = string
}

variable "key_name" {
  description = "EC2 Key Pair 이름"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "SSH 접속 허용 CIDR"
  type        = string
  default     = "0.0.0.0/0"
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}
