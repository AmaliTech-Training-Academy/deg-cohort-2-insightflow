variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  description = "Two public subnets in different AZs (ALB requirement)"
  type        = list(string)
}

variable "alb_security_group_id" {
  type = string
}

variable "ec2_instance_id" {
  description = "EC2 instance to register in target groups. Leave empty when using ECS (ECS module manages its own IP-based target groups)."
  type        = string
  default     = ""
}

variable "enable_https" {
  description = "Enable HTTPS (port 443) with TLS termination. Requires acm_certificate_arn. Set false in dev to use HTTP only."
  type        = bool
  default     = true
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for the HTTPS listener. Required when enable_https = true."
  type        = string
  default     = ""
}

variable "enable_deletion_protection" {
  description = "Prevent the ALB from being deleted via the API. Enable in prod."
  type        = bool
  default     = false
}

variable "enable_waf" {
  description = "Attach WAF v2 with AWS managed rules. Only enable in prod."
  type        = bool
  default     = false
}

variable "access_logs_bucket" {
  description = "S3 bucket name for ALB access logs. Leave empty to disable."
  type        = string
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}
