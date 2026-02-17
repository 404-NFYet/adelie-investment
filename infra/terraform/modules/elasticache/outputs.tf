output "endpoint" {
  description = "Redis 엔드포인트 (호스트명)"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "port" {
  description = "Redis 포트"
  value       = aws_elasticache_cluster.main.cache_nodes[0].port
}

output "security_group_id" {
  description = "Redis 보안 그룹 ID"
  value       = aws_security_group.redis.id
}
