variable "name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "region" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "alb_sg_id" {
  description = "ALB security group — allowed to reach ECS tasks"
  type        = string
}

variable "alb_listener_arn" {
  description = "ALB listener ARN to attach target groups to"
  type        = string
}

# ── Image URIs (pushed by CI) ─────────────────────────────────────────────────
variable "backend_image" {
  description = "Full ECR URI for the backend image (e.g. 123.dkr.ecr.eu-west-1.amazonaws.com/insightflow/backend:sha-abc)"
  type        = string
}

variable "frontend_image" {
  type = string
}

variable "etl_image" {
  type = string
}

# ── Secrets Manager ARNs (created by RDS/Redis modules) ──────────────────────
variable "app_db_secret_arn" {
  type = string
}

variable "warehouse_db_secret_arn" {
  type = string
}

variable "redis_secret_arn" {
  type = string
}

# ── Non-sensitive env vars ────────────────────────────────────────────────────
variable "django_settings_module" {
  type    = string
  default = "insightflow.settings.prod"
}

variable "allowed_hosts" {
  type    = string
  default = "*"
}

variable "cors_allowed_origins" {
  type    = string
  default = ""
}

variable "s3_bucket_name" {
  type = string
}

# ── Sizing ────────────────────────────────────────────────────────────────────
variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "worker_cpu" {
  type    = number
  default = 256
}

variable "worker_memory" {
  type    = number
  default = 512
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "tags" {
  type    = map(string)
  default = {}
}
