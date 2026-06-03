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

variable "developer_usernames" {
  description = "List of IAM usernames to create for dev tunnel access. e.g. [\"ssozi\", \"okeke\"]"
  type        = list(string)
  default     = []
}
