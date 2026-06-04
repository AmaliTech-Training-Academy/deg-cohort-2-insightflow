# ── Application entry point ───────────────────────────────────────────────────

output "alb_dns_name" {
  description = "Point your domain CNAME/ALIAS here"
  value       = module.alb.alb_dns_name
}

output "app_url" {
  value = "http://${module.alb.alb_dns_name}"
}

# ── ECR — image repository URLs ───────────────────────────────────────────────

output "ecr_backend_url" {
  description = "Push backend images: docker push <url>:tag"
  value       = module.ecr.backend_repository_url
}

output "ecr_frontend_url" {
  value = module.ecr.frontend_repository_url
}

output "ecr_etl_url" {
  value = module.ecr.etl_repository_url
}

# ── ECS ───────────────────────────────────────────────────────────────────────

output "ecs_cluster_name" {
  description = "Used by deploy-prod.yml: ECS_CLUSTER secret"
  value       = module.ecs.cluster_name
}

output "ecs_backend_service" {
  value = module.ecs.backend_service_name
}

output "ecs_frontend_service" {
  value = module.ecs.frontend_service_name
}

output "migration_task_definition_arn" {
  description = "Used by CI to run one-shot Django migration before deploy"
  value       = module.ecs.migration_task_definition_arn
}

output "ecs_task_security_group_id" {
  description = "Set as PROD_ECS_SG_ID GitHub secret for migration task networking"
  value       = module.ecs.task_security_group_id
}

# ── Database credentials ──────────────────────────────────────────────────────

output "db_credentials_app" {
  description = "Fetch app DB credentials from Secrets Manager"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-prod/db/app --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "db_credentials_warehouse" {
  value = "aws secretsmanager get-secret-value --secret-id insightflow-prod/db/warehouse --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "app_db_endpoint" {
  value = module.rds.app_db_endpoint
}

output "warehouse_db_endpoint" {
  value = module.rds.warehouse_db_endpoint
}

# ── Redis ─────────────────────────────────────────────────────────────────────

output "redis_endpoint" {
  value = module.redis.primary_endpoint
}

# ── Storage ───────────────────────────────────────────────────────────────────

output "uploads_bucket" {
  value = module.s3.bucket_name
}

# ── Secrets paths reference ───────────────────────────────────────────────────

output "secrets_paths" {
  description = "All Secrets Manager paths for this environment"
  value = {
    app_db       = "insightflow-prod/db/app"
    warehouse_db = "insightflow-prod/db/warehouse"
    redis        = "insightflow-prod/redis/endpoint"
  }
}
