variable "name" {
  type = string
}

variable "private_subnet_ids" {
  description = "List of ≥2 private subnet IDs for the ElastiCache subnet group"
  type        = list(string)
}

variable "redis_security_group_id" {
  type = string
}

variable "node_type" {
  description = "cache.t3.micro for dev (~$12/mo), cache.t3.small for prod (~$24/mo)"
  type        = string
  default     = "cache.t3.micro"
}

variable "maxmemory_policy" {
  description = "Redis eviction policy. allkeys-lru suits a general-purpose cache."
  type        = string
  default     = "allkeys-lru"
}

variable "transit_encryption_mode" {
  description = "'preferred' accepts both TLS and plain-text. 'required' enforces TLS only."
  type        = string
  default     = "preferred"
}

variable "snapshot_retention_days" {
  description = "Days to retain daily snapshots. 0 disables snapshots (dev). 1–35 for prod."
  type        = number
  default     = 0
}

variable "apply_immediately" {
  description = "Apply changes immediately (true for dev, false for prod to wait for maintenance window)"
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
