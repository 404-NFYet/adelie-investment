# Dev 환경 변수 정의

variable "aws_region" {
  default = "ap-northeast-2"
}

variable "project_name" {
  default = "adelie"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "public_subnets" {
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  default = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "azs" {
  default = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "bastion_key_name" {
  description = "EC2 Key Pair 이름"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "Bastion SSH 허용 CIDR"
  default     = "0.0.0.0/0"
}

variable "db_name" {
  default = "narrative_invest"
}

variable "db_username" {
  default = "narative"
}

variable "db_password" {
  description = "RDS 비밀번호"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "perplexity_api_key" {
  type      = string
  sensitive = true
}

variable "claude_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "kis_app_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "kis_app_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "jwt_secret" {
  type      = string
  sensitive = true
}
