output "bucket_names" {
  description = "S3 버킷 이름 맵"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket }
}

output "bucket_arns" {
  description = "S3 버킷 ARN 맵"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}
