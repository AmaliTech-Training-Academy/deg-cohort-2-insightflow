variable "region" {
  type    = string
  default = "eu-west-1"
}

variable "app_db_password" {
  type      = string
  sensitive = true
}

variable "warehouse_db_password" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  description = "Aiven Cloud Redis connection URL (rediss://...)"
  type        = string
  sensitive   = true
}

variable "cors_allowed_origins" {
  description = "Comma-separated frontend origins the API will accept"
  type        = string
  default     = ""
}
