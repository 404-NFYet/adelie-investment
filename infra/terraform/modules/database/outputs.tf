output "db_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "db_name" {
  value = aws_db_instance.postgres.db_name
}

output "redis_endpoint" {
  value     = aws_elasticache_cluster.redis.cache_nodes[0].address
  sensitive = true
}

output "redis_port" {
  value = aws_elasticache_cluster.redis.port
}
