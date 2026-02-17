# Adelie ECS 모듈 - Fargate 클러스터 + 서비스 + 태스크 정의

# --- ECS 클러스터 ---
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${var.project_name}-cluster" }
}

# --- CloudWatch 로그 그룹 ---
resource "aws_cloudwatch_log_group" "ecs" {
  for_each = toset(["frontend", "backend-api", "ai-pipeline"])

  name              = "/ecs/${var.project_name}-${each.value}"
  retention_in_days = 30

  tags = { Name = "${var.project_name}-${each.value}-logs" }
}

# --- ECS 태스크 실행 역할 ---
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project_name}-ecs-execution-role" }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Secrets Manager 읽기 권한
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${var.project_name}-ecs-secrets-policy"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = values(var.secrets_arns)
    }]
  })
}

# --- ECS 태스크 역할 (애플리케이션 권한) ---
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project_name}-ecs-task-role" }
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${var.project_name}-ecs-task-s3-policy"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = ["arn:aws:s3:::${var.project_name}-*", "arn:aws:s3:::${var.project_name}-*/*"]
    }]
  })
}

# --- ALB ---
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-alb-sg" }

  lifecycle { create_before_destroy = true }
}

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  tags = { Name = "${var.project_name}-alb" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# --- Target Groups ---
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = { Name = "${var.project_name}-frontend-tg" }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend-tg"
  port        = 8082
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api/v1/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = { Name = "${var.project_name}-backend-tg" }
}

# API 요청을 backend로 라우팅
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern { values = ["/api/*"] }
  }
}

# --- ECS 서비스 보안 그룹 ---
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-ecs-tasks-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-ecs-tasks-sg" }

  lifecycle { create_before_destroy = true }
}

# --- Frontend 태스크 정의 ---
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "frontend"
    image = "${var.ecr_urls["frontend"]}:latest"
    portMappings = [{ containerPort = 80, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs["frontend"].name
        "awslogs-region"        = "ap-northeast-2"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = { Name = "${var.project_name}-frontend-task" }
}

# --- Backend API 태스크 정의 ---
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "backend-api"
    image = "${var.ecr_urls["backend-api"]}:latest"
    portMappings = [{ containerPort = 8082, protocol = "tcp" }]
    environment = [
      { name = "DATABASE_URL", value = "postgresql+asyncpg://narative:password@${var.rds_endpoint}:5432/narrative_invest" },
      { name = "REDIS_URL", value = "redis://${var.redis_endpoint}:6379/0" },
    ]
    secrets = [
      { name = "OPENAI_API_KEY", valueFrom = lookup(var.secrets_arns, "openai-api-key", "") },
      { name = "JWT_SECRET", valueFrom = lookup(var.secrets_arns, "jwt-secret", "") },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs["backend-api"].name
        "awslogs-region"        = "ap-northeast-2"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = { Name = "${var.project_name}-backend-api-task" }
}

# --- AI Pipeline 태스크 정의 ---
resource "aws_ecs_task_definition" "ai_pipeline" {
  family                   = "${var.project_name}-ai-pipeline"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "ai-pipeline"
    image = "${var.ecr_urls["ai-pipeline"]}:latest"
    environment = [
      { name = "DATABASE_URL", value = "postgresql+asyncpg://narative:password@${var.rds_endpoint}:5432/narrative_invest" },
      { name = "REDIS_URL", value = "redis://${var.redis_endpoint}:6379/0" },
    ]
    secrets = [
      { name = "OPENAI_API_KEY", valueFrom = lookup(var.secrets_arns, "openai-api-key", "") },
      { name = "PERPLEXITY_API_KEY", valueFrom = lookup(var.secrets_arns, "perplexity-api-key", "") },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs["ai-pipeline"].name
        "awslogs-region"        = "ap-northeast-2"
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])

  tags = { Name = "${var.project_name}-ai-pipeline-task" }
}

# --- Frontend 서비스 ---
resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.http]

  tags = { Name = "${var.project_name}-frontend-svc" }
}

# --- Backend API 서비스 ---
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend-api"
    container_port   = 8082
  }

  depends_on = [aws_lb_listener.http]

  tags = { Name = "${var.project_name}-backend-api-svc" }
}
