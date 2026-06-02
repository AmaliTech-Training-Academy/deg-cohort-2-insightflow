terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

locals {
  repos = {
    backend = "insightflow/backend"
    etl     = "insightflow/etl"
  }
}

resource "aws_ecr_repository" "this" {
  for_each = local.repos

  name                 = each.value
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.tags, { Name = each.value })
}

resource "aws_ecr_lifecycle_policy" "this" {
  for_each   = aws_ecr_repository.this
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last ${var.images_to_keep} images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.images_to_keep
      }
      action = { type = "expire" }
    }]
  })
}
