variable "name" {
  type = string
}

variable "private_subnet_ids" {
  description = "List of ≥2 private subnet IDs for the RDS subnet group"
  type        = list(string)
}

variable "rds_security_group_id" {
  type = string
}

variable "instance_class" {
  description = "db.t3.micro for dev, db.t3.small for prod"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage_gb" {
  type    = number
  default = 20
}

variable "app_db_password" {
  description = "Master password for the app DB. Pass via TF_VAR or tfvars (sensitive)."
  type        = string
  sensitive   = true
}

variable "warehouse_db_password" {
  description = "Master password for the warehouse DB."
  type        = string
  sensitive   = true
}

variable "multi_az" {
  description = "Enable Multi-AZ standby. false for dev, true for prod."
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "true for dev (fast destroy), false for prod."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Prevent accidental deletion. false for dev, true for prod."
  type        = bool
  default     = false
}

variable "publicly_accessible" {
  description = "Assign a public IP to RDS so it is reachable without a tunnel. Enable in dev only — never in prod."
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "1 for dev, 7 for prod."
  type        = number
  default     = 1
}

variable "enable_performance_insights" {
  description = "Free tier available for db.t3 instances — enable in prod."
  type        = bool
  default     = false
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds. 0 disables it (dev). 60 for prod."
  type        = number
  default     = 0
}

variable "tags" {
  type    = map(string)
  default = {}
}
