variable "project_name" {
  description = "프로젝트 이름 (리소스 접두사)"
  type        = string
}

variable "buckets" {
  description = "생성할 S3 버킷 이름 목록 (project_name- 접두사 자동 추가)"
  type        = list(string)
  default     = ["naver-reports", "extracted-data"]
}
