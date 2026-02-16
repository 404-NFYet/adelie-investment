output "secret_arns" {
  description = "시크릿 ARN 맵 (키명 → ARN)"
  value       = { for k, v in aws_secretsmanager_secret.secrets : k => v.arn }
}

output "secret_names" {
  description = "시크릿 이름 맵 (키명 → 전체 이름)"
  value       = { for k, v in aws_secretsmanager_secret.secrets : k => v.name }
}
