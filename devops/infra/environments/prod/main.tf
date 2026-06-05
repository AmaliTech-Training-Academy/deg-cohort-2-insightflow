terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  # Uncomment after creating the S3 bucket + DynamoDB table (see bootstrap/)
  # backend "s3" {
  #   bucket         = "insightflow-tfstate"
  #   key            = "prod/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "insightflow-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = local.common_tags
  }
}

locals {
  name = "insightflow-prod"
  common_tags = {
    Project     = "InsightFlow"
    Environment = "prod"
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}

# ── S3 ────────────────────────────────────────────────────────────────────────
module "s3" {
  source             = "../../modules/s3"
  bucket_name        = "${local.name}-uploads-${data.aws_caller_identity.current.account_id}"
  versioning_enabled = true
  tags               = local.common_tags
}

# ── Network ───────────────────────────────────────────────────────────────────
module "vpc" {
  source         = "../../modules/vpc"
  name           = local.name
  region         = var.region
  vpc_cidr       = "10.0.0.0/16"
  public_cidr_a  = "10.0.1.0/24"
  public_cidr_b  = "10.0.2.0/24"
  private_cidr_a = "10.0.10.0/24"
  private_cidr_b = "10.0.11.0/24"
  tags           = local.common_tags
}

# ── Security groups ───────────────────────────────────────────────────────────
module "security_groups" {
  source     = "../../modules/security-groups"
  name       = local.name
  vpc_id     = module.vpc.vpc_id
  enable_alb = true
  enable_ssh = false # no shell access to compute in prod
  tags       = local.common_tags
}

# ── ECR — container image repositories ───────────────────────────────────────
module "ecr" {
  source         = "../../modules/ecr"
  images_to_keep = 10
  tags           = local.common_tags
}

# ── RDS ───────────────────────────────────────────────────────────────────────
# Redis is provided by Aiven Cloud (not ElastiCache) — no module needed.
module "rds" {
  source                = "../../modules/rds"
  name                  = local.name
  private_subnet_ids    = module.vpc.private_subnet_ids
  rds_security_group_id = module.security_groups.rds_sg_id
  instance_class        = "db.t3.small"
  allocated_storage_gb  = 20
  app_db_password       = var.app_db_password
  warehouse_db_password = var.warehouse_db_password

  multi_az                    = false
  skip_final_snapshot         = false
  deletion_protection         = true
  backup_retention_days       = 7
  enable_performance_insights = true
  monitoring_interval         = 60

  tags = local.common_tags
}

# ── Secrets Manager — Redis (Aiven Cloud) ─────────────────────────────────────
# Aiven Redis is used instead of ElastiCache. The URL is stored here so
# ECS task definitions can inject it into containers via the secrets: block.
resource "aws_secretsmanager_secret" "redis" {
  name                    = "insightflow-prod/redis/endpoint"
  description             = "Aiven Cloud Redis connection URL for prod"
  recovery_window_in_days = 0 # allow immediate re-creation if needed
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis" {
  secret_id = aws_secretsmanager_secret.redis.id
  secret_string = jsonencode({
    url = var.redis_url
  })
}

# ── ALB ───────────────────────────────────────────────────────────────────────
# HTTP only — no ACM certificate required.
# WAF v2 is attached for OWASP Top 10 + rate limiting.
module "alb" {
  source                     = "../../modules/alb"
  name                       = local.name
  vpc_id                     = module.vpc.vpc_id
  public_subnet_ids          = module.vpc.public_subnet_ids
  alb_security_group_id      = module.security_groups.alb_sg_id
  enable_https               = false
  enable_deletion_protection = true
  enable_waf                 = true
  tags                       = local.common_tags
}

# ── ECS Fargate — application cluster ────────────────────────────────────────
module "ecs" {
  source = "../../modules/ecs"

  name   = local.name
  region = var.region

  # Network
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  # ALB SG — ECS module creates its own tasks SG allowing inbound from this
  alb_sg_id = module.security_groups.alb_sg_id

  # ALB — ECS attaches its own IP-based target groups to this listener
  alb_listener_arn = module.alb.http_listener_arn

  # Secrets Manager ARNs injected into containers at runtime
  app_db_secret_arn       = module.rds.app_db_secret_arn
  warehouse_db_secret_arn = module.rds.warehouse_db_secret_arn
  redis_secret_arn        = aws_secretsmanager_secret.redis.arn

  # S3 for media uploads
  s3_bucket_name = module.s3.bucket_name

  # Initial image URIs — CI/CD updates task definitions after first apply
  backend_image  = "${module.ecr.backend_repository_url}:latest"
  frontend_image = "${module.ecr.frontend_repository_url}:latest"
  etl_image      = "${module.ecr.etl_repository_url}:latest"

  # App config
  allowed_hosts        = "*"
  cors_allowed_origins = var.cors_allowed_origins

  # Sizing
  backend_cpu     = 512
  backend_memory  = 1024
  frontend_cpu    = 256
  frontend_memory = 512
  worker_cpu      = 256
  worker_memory   = 512

  log_retention_days = 30

  tags = local.common_tags
}
