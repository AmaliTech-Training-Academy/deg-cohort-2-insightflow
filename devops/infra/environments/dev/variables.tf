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
