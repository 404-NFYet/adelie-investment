output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}

output "frontend_bucket_arn" {
  value = aws_s3_bucket.frontend.arn
}

output "media_bucket_name" {
  value = aws_s3_bucket.media.bucket
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend_api.repository_url
}

output "ecr_repository_arn" {
  value = aws_ecr_repository.backend_api.arn
}
