output "public_ip" {
  description = "Bastion 퍼블릭 IP"
  value       = aws_instance.bastion.public_ip
}

output "instance_id" {
  description = "Bastion EC2 인스턴스 ID"
  value       = aws_instance.bastion.id
}

output "security_group_id" {
  description = "Bastion 보안 그룹 ID"
  value       = aws_security_group.bastion.id
}
