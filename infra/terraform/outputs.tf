output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "alb_dns_name" {
  description = "ALB DNS 이름 (CNAME 등록용)"
  value       = module.compute.alb_dns_name
}

output "cloudfront_domain" {
  description = "CloudFront 배포 도메인 (프론트엔드)"
  value       = module.cdn.cloudfront_domain_name
}

output "ecr_repository_url" {
  description = "ECR 저장소 URL (CI/CD 이미지 푸시용)"
  value       = module.storage.ecr_repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL 엔드포인트"
  value       = module.database.db_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis 엔드포인트"
  value       = module.database.redis_endpoint
  sensitive   = true
}

output "s3_frontend_bucket" {
  description = "프론트엔드 정적 파일 S3 버킷 이름"
  value       = module.storage.frontend_bucket_name
}
