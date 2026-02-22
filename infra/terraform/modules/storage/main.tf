/**
 * storage 모듈
 * S3 (프론트엔드 정적 파일, MinIO 대체), ECR (컨테이너 이미지)
 */

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ── S3: 프론트엔드 정적 파일 ──
resource "aws_s3_bucket" "frontend" {
  bucket = "${var.project_name}-${var.environment}-frontend"

  tags = {
    Name        = "${var.project_name}-${var.environment}-frontend"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ── S3: 미디어/업로드 파일 (MinIO 대체) ──
resource "aws_s3_bucket" "media" {
  bucket = "${var.project_name}-${var.environment}-media"

  tags = {
    Name        = "${var.project_name}-${var.environment}-media"
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_cors_configuration" "media" {
  bucket = aws_s3_bucket.media.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["https://*.${var.domain_name}"]
    max_age_seconds = 3000
  }
}

# ── ECR: 백엔드 API 이미지 ──
resource "aws_ecr_repository" "backend_api" {
  name                 = "${var.project_name}/backend-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_ecr_lifecycle_policy" "backend_api" {
  repository = aws_ecr_repository.backend_api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "최신 이미지 10개만 유지"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 10
        }
        action = { type = "expire" }
      }
    ]
  })
}
