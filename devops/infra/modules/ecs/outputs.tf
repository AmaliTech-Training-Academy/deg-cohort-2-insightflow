output "cluster_name" {
  value = aws_ecs_cluster.this.name
}

output "cluster_arn" {
  value = aws_ecs_cluster.this.arn
}

output "backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "celery_service_name" {
  value = aws_ecs_service.celery.name
}

output "etl_listener_service_name" {
  value = aws_ecs_service.etl_listener.name
}

output "etl_worker_service_name" {
  value = aws_ecs_service.etl_worker.name
}

output "migration_task_definition_arn" {
  description = "Used by CI to run one-shot migration before deploy"
  value       = aws_ecs_task_definition.migration.arn
}

output "task_security_group_id" {
  value = aws_security_group.tasks.id
}
