variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "subnet_id" {
  description = "Subnet to place the EC2 instance in. Use a public subnet + enable_public_ip=true for dev SSH access."
  type        = string
}

variable "enable_public_ip" {
  description = "Assign a public IP. True in dev (enables SSH). False in prod (SSM-only via NAT)."
  type        = bool
  default     = false
}

variable "key_name" {
  description = "Name of an existing AWS key pair for SSH. Required when enable_public_ip = true. Leave null in prod."
  type        = string
  default     = null
}

variable "security_group_id" {
  type = string
}

variable "instance_type" {
  description = "t3.small for dev, t3.medium for prod"
  type        = string
  default     = "t3.small"
}

variable "root_volume_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

variable "s3_bucket_name" {
  description = "S3 bucket the EC2 IAM role gets read/write access to"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention. 7 for dev, 30 for prod."
  type        = number
  default     = 7
}

variable "tags" {
  type    = map(string)
  default = {}
}
