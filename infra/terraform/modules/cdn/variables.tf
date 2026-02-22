variable "project_name"                     { type = string }
variable "environment"                      { type = string }
variable "frontend_bucket_name"             { type = string }
variable "frontend_bucket_arn"              { type = string }
variable "frontend_bucket_regional_domain"  { type = string }
variable "acm_certificate_arn"              { type = string }
variable "domain_aliases"                   { type = list(string); default = [] }
