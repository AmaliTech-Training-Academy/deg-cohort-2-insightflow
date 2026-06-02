variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "app_db_password" {
  type      = string
  sensitive = true
}

variable "warehouse_db_password" {
  type      = string
  sensitive = true
}

variable "acm_certificate_arn" {
  description = "ARN of an ACM certificate covering your domain (must be in the same region as the ALB)"
  type        = string
}
