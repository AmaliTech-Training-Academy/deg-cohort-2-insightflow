output "alb_dns_name" {
  description = "Create a CNAME / ALIAS record pointing your domain to this"
  value       = module.alb.alb_dns_name
}

output "ec2_instance_id" {
  description = "Use this with: aws ssm start-session --target <id>"
  value       = module.ec2.instance_id
}

output "app_db_endpoint" {
  value = module.rds.app_db_endpoint
}

output "warehouse_db_endpoint" {
  value = module.rds.warehouse_db_endpoint
}

output "redis_endpoint" {
  description = "Set as REDIS_URL in the application — rediss://<host>:6379/0"
  value       = module.redis.redis_url
}

output "backend_ecr_url" {
  value = module.ecr.backend_repository_url
}

output "etl_ecr_url" {
  value = module.ecr.etl_repository_url
}

output "uploads_bucket" {
  value = module.s3.bucket_name
}
