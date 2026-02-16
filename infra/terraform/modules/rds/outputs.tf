output "endpoint" {
  description = "RDS 엔드포인트 (호스트명)"
  value       = aws_db_instance.main.address
}

output "port" {
  description = "RDS 포트"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "데이터베이스 이름"
  value       = aws_db_instance.main.db_name
}

output "security_group_id" {
  description = "RDS 보안 그룹 ID"
  value       = aws_security_group.rds.id
}
