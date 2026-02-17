variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}

variable "services" {
  description = "ECR 레포지토리를 생성할 서비스 목록"
  type        = list(string)
  default     = ["frontend", "backend-api", "ai-pipeline"]
}
