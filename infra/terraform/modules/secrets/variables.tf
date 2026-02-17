variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}

variable "secrets" {
  description = "시크릿 맵 (키명 → 값)"
  type        = map(string)
  sensitive   = true
}
