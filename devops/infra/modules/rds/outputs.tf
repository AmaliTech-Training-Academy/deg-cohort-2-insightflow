output "app_db_endpoint" {
  description = "Hostname of the app DB (use in DB_HOST env var)"
  value       = aws_db_instance.app.address
}

output "warehouse_db_endpoint" {
  description = "Hostname of the warehouse DB"
  value       = aws_db_instance.warehouse.address
}

output "app_db_secret_arn" {
  value = aws_secretsmanager_secret.app_db.arn
}

output "warehouse_db_secret_arn" {
  value = aws_secretsmanager_secret.warehouse_db.arn
}
