output "cluster_id" {
  description = "ECS 클러스터 ID"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "ECS 클러스터 이름"
  value       = aws_ecs_cluster.main.name
}

output "alb_dns_name" {
  description = "ALB DNS 이름"
  value       = aws_lb.main.dns_name
}

output "alb_arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "frontend_service_name" {
  description = "Frontend ECS 서비스 이름"
  value       = aws_ecs_service.frontend.name
}

output "backend_service_name" {
  description = "Backend API ECS 서비스 이름"
  value       = aws_ecs_service.backend.name
}

output "ecs_security_group_id" {
  description = "ECS 태스크 보안 그룹 ID"
  value       = aws_security_group.ecs_tasks.id
}
