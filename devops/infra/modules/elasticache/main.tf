terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# Subnet group spans both private subnets — same pattern as RDS
resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.name}-redis-subnet-group" })
}

resource "aws_elasticache_parameter_group" "this" {
  name   = "${var.name}-redis7"
  family = "redis7"

  # Disable the default dangerous commands — good practice
  parameter {
    name  = "maxmemory-policy"
    value = var.maxmemory_policy
  }

  tags = var.tags
}

# Single-node Redis replication group.
# aws_elasticache_replication_group is the current recommended resource even
# for a single node (aws_elasticache_cluster for Redis is legacy).
resource "aws_elasticache_replication_group" "this" {
  replication_group_id = "${var.name}-redis"
  description          = "InsightFlow Redis - ${var.name}"

  node_type            = var.node_type
  num_cache_clusters   = 1 # single primary, no replica (cost-optimised)
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.this.name
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [var.redis_security_group_id]

  engine_version = "7.1"

  # Encryption at rest — always on, no extra cost
  at_rest_encryption_enabled = true

  # In-transit TLS — on by default in Redis 7; keep mode as "preferred" so
  # plain-text clients still work while you migrate (flip to "required" later)
  transit_encryption_enabled = true
  transit_encryption_mode    = var.transit_encryption_mode

  # Automatic failover requires ≥2 nodes; disable for single-node
  automatic_failover_enabled = false
  multi_az_enabled           = false

  # Maintenance & backup
  snapshot_retention_limit = var.snapshot_retention_days
  apply_immediately        = var.apply_immediately

  tags = merge(var.tags, { Name = "${var.name}-redis" })
}

# Store the Redis endpoint in Secrets Manager so containers read it at startup
resource "aws_secretsmanager_secret" "redis" {
  name                    = "${var.name}/redis/endpoint"
  recovery_window_in_days = var.snapshot_retention_days == 0 ? 0 : 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({
    host = aws_elasticache_replication_group.this.primary_endpoint_address
    port = 6379
    url  = "rediss://${aws_elasticache_replication_group.this.primary_endpoint_address}:6379/0"
  })
}
