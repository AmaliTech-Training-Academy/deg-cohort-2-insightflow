output "backend_repository_url" {
  value = aws_ecr_repository.this["backend"].repository_url
}

output "etl_repository_url" {
  value = aws_ecr_repository.this["etl"].repository_url
}

output "registry_id" {
  value = aws_ecr_repository.this["backend"].registry_id
}
