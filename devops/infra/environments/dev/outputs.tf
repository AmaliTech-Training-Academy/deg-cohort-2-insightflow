# ── Application ───────────────────────────────────────────────────────────────

output "app_url" {
  description = "Application URL (HTTP in dev)"
  value       = "http://${module.alb.alb_dns_name}"
}

output "api_docs_url" {
  description = "Swagger / OpenAPI docs"
  value       = "http://${module.alb.alb_dns_name}/api-docs/"
}

output "alb_dns_name" {
  description = "Raw ALB hostname"
  value       = module.alb.alb_dns_name
}

# ── EC2 / shell access ────────────────────────────────────────────────────────

output "ec2_instance_id" {
  value = module.ec2.instance_id
}

output "ec2_public_ip" {
  value = module.ec2.public_ip
}

output "ssh_command" {
  description = "Direct SSH (key written to ~/.ssh/insightflow-dev.pem by Terraform)"
  value       = "ssh -i ~/.ssh/insightflow-dev.pem ec2-user@${module.ec2.public_ip}"
}

output "ssm_command" {
  description = "Shell via SSM — no key needed, works even if SSH is closed"
  value       = "aws ssm start-session --target ${module.ec2.instance_id} --region ${var.region}"
}

# ── Database credentials ──────────────────────────────────────────────────────
# All secrets live in AWS Secrets Manager. Retrieve them with the commands below,
# then use the SSH tunnel commands to connect your local tools.

output "db_credentials_app" {
  description = "Step 1 — fetch the app DB credentials JSON from Secrets Manager"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-dev/db/app --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "db_credentials_warehouse" {
  description = "Step 1 — fetch the warehouse DB credentials JSON from Secrets Manager"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-dev/db/warehouse --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "app_db_endpoint" {
  description = "App DB hostname — connect directly (no tunnel needed in dev)"
  value       = module.rds.app_db_endpoint
}

output "app_db_direct_url" {
  description = "Ready-to-use connection URL — paste into DBeaver, psql, or .env"
  value       = "postgresql://insightflow:${var.app_db_password}@${module.rds.app_db_endpoint}:5432/insightflow_app"
  sensitive   = true
}

output "app_db_tunnel_command" {
  description = "Step 2 — open SSH tunnel (run in a separate terminal, keep it open)"
  value       = "ssh -i ~/.ssh/insightflow-dev.pem -L 5432:${module.rds.app_db_endpoint}:5432 ec2-user@${module.ec2.public_ip} -N -f"
}

output "app_db_psql_command" {
  description = "Step 3 — connect psql to the tunnel (replace PASSWORD from Step 1)"
  value       = "psql -h localhost -p 5432 -U insightflow_user -d insightflow_app"
}

output "warehouse_db_endpoint" {
  description = "Warehouse DB hostname — connect directly (no tunnel needed in dev)"
  value       = module.rds.warehouse_db_endpoint
}

output "warehouse_db_direct_url" {
  description = "Ready-to-use connection URL for the warehouse DB"
  value       = "postgresql://insightflow_wh:${var.warehouse_db_password}@${module.rds.warehouse_db_endpoint}:5432/insightflow_warehouse"
  sensitive   = true
}

output "warehouse_db_tunnel_command" {
  description = "Step 2 — open SSH tunnel for warehouse DB (port 5433 to avoid clash with app DB)"
  value       = "ssh -i ~/.ssh/insightflow-dev.pem -L 5433:${module.rds.warehouse_db_endpoint}:5432 ec2-user@${module.ec2.public_ip} -N -f"
}

output "warehouse_db_psql_command" {
  description = "Step 3 — connect psql to the warehouse tunnel (replace PASSWORD from Step 1)"
  value       = "psql -h localhost -p 5433 -U insightflow_user -d insightflow_warehouse"
}

# ── Redis credentials ─────────────────────────────────────────────────────────

output "redis_credentials" {
  description = "Step 1 — fetch Redis connection details from Secrets Manager"
  value       = "aws secretsmanager get-secret-value --secret-id insightflow-dev/redis/endpoint --region ${var.region} --query SecretString --output text | python3 -m json.tool"
}

output "redis_endpoint" {
  description = "Redis hostname (private — reach via SSH tunnel below)"
  value       = module.redis.primary_endpoint
}

output "redis_tunnel_command" {
  description = "Step 2 — open SSH tunnel for Redis"
  value       = "ssh -i ~/.ssh/insightflow-dev.pem -L 6379:${module.redis.primary_endpoint}:6379 ec2-user@${module.ec2.public_ip} -N -f"
}

output "redis_cli_command" {
  description = "Step 3 — connect redis-cli through the tunnel"
  value       = "redis-cli -h localhost -p 6379"
}

output "redis_url" {
  description = "Full Redis URL (used inside EC2 by the app)"
  value       = module.redis.redis_url
}

# ── Storage ───────────────────────────────────────────────────────────────────

output "uploads_bucket" {
  value = module.s3.bucket_name
}

# ── Secrets paths reference ───────────────────────────────────────────────────

output "secrets_paths" {
  description = "All Secrets Manager paths for this environment"
  value = {
    app_db       = "insightflow-dev/db/app"
    warehouse_db = "insightflow-dev/db/warehouse"
    redis        = "insightflow-dev/redis/endpoint"
  }
}
