# ── Application ───────────────────────────────────────────────────────────────

output "alb_dns_name" {
  description = "Create a CNAME / ALIAS record pointing your domain to this"
  value       = module.alb.alb_dns_name
}

# ── EC2 / shell access ────────────────────────────────────────────────────────

output "ec2_instance_id" {
  description = "Use with SSM — no SSH key or open port 22 required"
  value       = module.ec2.instance_id
}

output "ssm_command" {
  description = "Shell access via SSM Session Manager"
  value       = "aws ssm start-session --target ${module.ec2.instance_id} --region ${var.region}"
}

# ── Database credentials ──────────────────────────────────────────────────────

output "db_credentials_app" {
  description = "Fetch app DB credentials — run from a machine with appropriate IAM permissions"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-prod/db/app --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "db_credentials_warehouse" {
  description = "Fetch warehouse DB credentials"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-prod/db/warehouse --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "app_db_endpoint" {
  description = "App DB hostname — connect via SSM port-forward: aws ssm start-session --target <id> --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=<endpoint>,portNumber=5432,localPortNumber=5432"
  value       = module.rds.app_db_endpoint
}

output "warehouse_db_endpoint" {
  value = module.rds.warehouse_db_endpoint
}

# ── Redis credentials ─────────────────────────────────────────────────────────

output "redis_credentials" {
  description = "Fetch Redis connection details from Secrets Manager"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-prod/redis/endpoint --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

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
