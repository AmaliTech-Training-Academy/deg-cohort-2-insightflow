variable "bucket_name" {
  description = "Globally unique bucket name. Use account ID suffix to guarantee uniqueness."
  type        = string
}

variable "versioning_enabled" {
  description = "Enable versioning. Recommended for prod, off for dev to reduce storage cost."
  type        = bool
  default     = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
