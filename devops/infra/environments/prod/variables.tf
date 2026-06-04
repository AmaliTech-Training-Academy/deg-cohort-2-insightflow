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

variable "cors_allowed_origins" {
  description = "Comma-separated list of frontend origins the API will accept (e.g. https://app.example.com)"
  type        = string
  default     = ""
}

