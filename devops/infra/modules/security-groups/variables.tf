variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "enable_alb" {
  description = "Create ALB SG and lock EC2 ingress to it. Set true whenever an ALB is deployed."
  type        = bool
  default     = true
}

variable "enable_ssh" {
  description = "Allow SSH (port 22) inbound to EC2. Enable in dev/testing only — never in prod."
  type        = bool
  default     = false
}


variable "allow_public_db_access" {
  description = "Open RDS port 5432 to the internet. Dev only — lets developers connect directly with just the endpoint URL."
  type        = bool
  default     = false
}

variable "db_public_cidr_blocks" {
  description = "CIDRs allowed to reach RDS directly. Only used when allow_public_db_access = true."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allow_public_redis_access" {
  description = "Open Redis port 6379 to the specified CIDRs. Dev only — for direct troubleshooting. Note: ElastiCache has no public IP; still requires VPN or SSH tunnel."
  type        = bool
  default     = false
}

variable "redis_public_cidr_blocks" {
  description = "CIDRs allowed to reach Redis directly. Only used when allow_public_redis_access = true."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "allow_redis_proxy" {
  description = "Open EC2 port 6380 (Redis socat proxy) to the internet. Dev only — exposes a TCP proxy to the Redis cluster for external troubleshooting."
  type        = bool
  default     = false
}

variable "redis_proxy_cidr_blocks" {
  description = "CIDRs allowed to reach the EC2 Redis proxy on port 6380. Only used when allow_redis_proxy = true."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "ssh_cidr_blocks" {
  description = "CIDRs allowed to SSH into EC2. Only used when enable_ssh = true."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
