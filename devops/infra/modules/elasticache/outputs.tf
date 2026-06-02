output "primary_endpoint" {
  description = "Redis primary hostname — use in REDIS_HOST env var"
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "port" {
  value = 6379
}

output "redis_url" {
  description = "Full rediss:// URL for Django CACHES or Celery BROKER_URL"
  value       = "rediss://${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0"
}

output "secret_arn" {
  description = "Secrets Manager ARN — EC2 IAM role already has read access"
  value       = aws_secretsmanager_secret.redis.arn
}
