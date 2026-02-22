/**
 * compute 모듈
 * ECS Cluster, Fargate Task Definition, ECS Service, ALB
 */

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ── ECS Cluster ──
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = var.environment == "prod" ? "enabled" : "disabled"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ── IAM Role: ECS Task 실행 ──
data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${var.project_name}-${var.environment}-ecs-exec-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Secrets Manager 읽기 권한 추가
resource "aws_iam_role_policy" "ecs_secrets" {
  name = "${var.project_name}-${var.environment}-ecs-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "ssm:GetParameters",
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })
}

# ── ALB ──
resource "aws_lb" "main" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "backend_api" {
  name        = "${var.project_name}-${var.environment}-api"
  port        = 8082
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend_api.arn
  }
}

# ── ECS Task Definition ──
resource "aws_ecs_task_definition" "backend_api" {
  family                   = "${var.project_name}-${var.environment}-backend-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([
    {
      name      = "backend-api"
      image     = "${var.ecr_repository_url}:${var.ecr_image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 8082
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment }
      ]
      secrets = [
        { name = "DATABASE_URL",        valueFrom = "${var.secrets_arn}:DATABASE_URL::" },
        { name = "REDIS_URL",           valueFrom = "${var.secrets_arn}:REDIS_URL::" },
        { name = "OPENAI_API_KEY",      valueFrom = "${var.secrets_arn}:OPENAI_API_KEY::" },
        { name = "PERPLEXITY_API_KEY",  valueFrom = "${var.secrets_arn}:PERPLEXITY_API_KEY::" },
        { name = "LANGCHAIN_API_KEY",   valueFrom = "${var.secrets_arn}:LANGCHAIN_API_KEY::" },
        { name = "SECRET_KEY",          valueFrom = "${var.secrets_arn}:SECRET_KEY::" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}-${var.environment}/backend-api"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ── CloudWatch Log Group ──
resource "aws_cloudwatch_log_group" "backend_api" {
  name              = "/ecs/${var.project_name}-${var.environment}/backend-api"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ── ECS Service ──
resource "aws_ecs_service" "backend_api" {
  name            = "${var.project_name}-${var.environment}-backend-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend_api.arn
  desired_count   = var.backend_desired_count

  # staging: FARGATE_SPOT으로 비용 절감 / prod: FARGATE
  capacity_provider_strategy {
    capacity_provider = var.environment == "prod" ? "FARGATE" : "FARGATE_SPOT"
    weight            = 1
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend_api.arn
    container_name   = "backend-api"
    container_port   = 8082
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  deployment_controller {
    type = "ECS"
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }

  depends_on = [aws_lb_listener.https]
}
