variable "name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "region" {
  description = "AWS region (e.g. eu-west-1)"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "public_cidr_a" {
  description = "Public subnet CIDR for AZ-a"
  type        = string
}

variable "public_cidr_b" {
  description = "Public subnet CIDR for AZ-b"
  type        = string
}

variable "private_cidr_a" {
  description = "Private subnet CIDR for AZ-a (EC2 lives here)"
  type        = string
}

variable "private_cidr_b" {
  description = "Private subnet CIDR for AZ-b (spare; spans RDS subnet group)"
  type        = string
}

variable "enable_nat_gateway" {
  description = "Create a NAT Gateway (and its EIP) for private-subnet outbound internet. Set false in dev where no private resource needs outbound access."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
