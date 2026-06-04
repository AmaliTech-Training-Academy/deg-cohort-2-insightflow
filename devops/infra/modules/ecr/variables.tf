variable "images_to_keep" {
  description = "Number of images to retain per repository. 5 for dev, 10 for prod."
  type        = number
  default     = 5
}

variable "tags" {
  type    = map(string)
  default = {}
}
