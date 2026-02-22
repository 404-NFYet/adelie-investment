variable "project_name" { type = string }
variable "environment"  { type = string }
variable "private_subnet_ids"    { type = list(string) }
variable "rds_security_group_id" { type = string }
variable "redis_security_group_id" { type = string }
variable "db_instance_class"    { type = string; default = "db.t3.micro" }
variable "db_allocated_storage" { type = number; default = 20 }
variable "db_name"     { type = string; default = "narrative_invest" }
variable "db_username" { type = string; default = "narative" }
variable "db_password" { type = string; sensitive = true }
variable "redis_node_type" { type = string; default = "cache.t4g.micro" }
