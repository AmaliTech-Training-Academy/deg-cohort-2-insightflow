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

variable "ssh_cidr_blocks" {
  description = "CIDRs allowed to SSH into EC2. Only used when enable_ssh = true."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
