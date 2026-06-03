variable "aws_region" {
  description = "AWS region where the OIDC provider is registered"
  type        = string
  default     = "eu-west-1"
}

variable "github_org" {
  description = "GitHub organisation or user that owns the repository"
  type        = string
  default     = "AmaliTech-Training-Academy"
}

variable "github_repo" {
  description = "GitHub repository name (without the org prefix)"
  type        = string
  default     = "deg-cohort-2-insightflow"
}
