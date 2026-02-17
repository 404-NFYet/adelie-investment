# Adelie ElastiCache 모듈 - Redis 7

# --- 보안 그룹 ---
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Redis from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-redis-sg" }

  lifecycle { create_before_destroy = true }
}

# --- 서브넷 그룹 ---
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-redis-subnet"
  subnet_ids = var.private_subnet_ids

  tags = { Name = "${var.project_name}-redis-subnet" }
}

# --- 파라미터 그룹 ---
resource "aws_elasticache_parameter_group" "redis7" {
  name   = "${var.project_name}-redis7-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = { Name = "${var.project_name}-redis7-params" }
}

# --- Redis 클러스터 (단일 노드) ---
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.project_name}-redis"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.node_type
  num_cache_nodes      = 1
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.redis7.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  snapshot_retention_limit = 1
  maintenance_window       = "sun:05:00-sun:06:00"

  tags = { Name = "${var.project_name}-redis" }
}
