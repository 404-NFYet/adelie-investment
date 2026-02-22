variable "project_name"          { type = string }
variable "environment"           { type = string }
variable "aws_region"            { type = string; default = "ap-northeast-2" }
variable "vpc_id"                { type = string }
variable "public_subnet_ids"     { type = list(string) }
variable "private_subnet_ids"    { type = list(string) }
variable "alb_security_group_id" { type = string }
variable "ecs_security_group_id" { type = string }
variable "ecr_repository_url"    { type = string }
variable "ecr_image_tag"         { type = string; default = "latest" }
variable "backend_cpu"           { type = number; default = 512 }
variable "backend_memory"        { type = number; default = 1024 }
variable "backend_desired_count" { type = number; default = 1 }
variable "acm_certificate_arn"   { type = string }
variable "secrets_arn"           { type = string; description = "AWS Secrets Manager ARN (API 키 등)" }
