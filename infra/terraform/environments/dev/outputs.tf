# Dev 환경 출력값

output "alb_url" {
  description = "Application Load Balancer URL"
  value       = module.ecs.alb_dns_name
}

output "bastion_ip" {
  description = "Bastion Host Public IP"
  value       = module.bastion.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL Endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache Redis Endpoint"
  value       = module.elasticache.endpoint
}

output "ecr_urls" {
  description = "ECR Repository URLs"
  value       = module.ecr.repository_urls
}

output "s3_buckets" {
  description = "S3 Bucket Names"
  value       = module.s3.bucket_names
}
