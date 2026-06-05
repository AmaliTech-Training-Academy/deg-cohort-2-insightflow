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
  description = "Set as ECS_CLUSTER GitHub secret"
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
  description = "Set as PROD_ECS_SG_ID GitHub secret"
  value       = module.ecs.task_security_group_id
}

# ── Database ──────────────────────────────────────────────────────────────────

output "app_db_endpoint" {
  value = module.rds.app_db_endpoint
}

output "warehouse_db_endpoint" {
  value = module.rds.warehouse_db_endpoint
}

# ── Network ───────────────────────────────────────────────────────────────────

output "private_subnet_ids" {
  description = "Set as PROD_PRIVATE_SUBNET_IDS GitHub secret"
  value       = join(",", module.vpc.private_subnet_ids)
}

# ── Storage ───────────────────────────────────────────────────────────────────

output "uploads_bucket" {
  value = module.s3.bucket_name
}

# ── Secrets paths ─────────────────────────────────────────────────────────────

output "secrets_paths" {
  value = {
    app_db       = "insightflow-prod/db/app"
    warehouse_db = "insightflow-prod/db/warehouse"
    redis        = "insightflow-prod/redis/endpoint"
  }
}
