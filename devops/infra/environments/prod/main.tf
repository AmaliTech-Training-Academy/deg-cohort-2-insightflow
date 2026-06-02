terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  # Uncomment after creating the S3 bucket + DynamoDB table (see bootstrap/)
  # backend "s3" {
  #   bucket         = "insightflow-tfstate"
  #   key            = "prod/terraform.tfstate"
  #   region         = "ap-southeast-1"
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
  enable_ssh = false # no SSH in prod — use SSM Session Manager
  tags       = local.common_tags
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
module "ec2" {
  source             = "../../modules/ec2"
  name               = local.name
  region             = var.region
  subnet_id          = module.vpc.private_subnet_a_id
  security_group_id  = module.security_groups.ec2_sg_id
  instance_type      = "t3.medium"
  root_volume_gb     = 30
  enable_public_ip   = false # prod: SSM-only access through NAT GW
  s3_bucket_name     = module.s3.bucket_name
  log_retention_days = 30
  tags               = local.common_tags
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────
module "redis" {
  source                  = "../../modules/elasticache"
  name                    = local.name
  private_subnet_ids      = module.vpc.private_subnet_ids
  redis_security_group_id = module.security_groups.redis_sg_id
  node_type               = "cache.t3.small"
  transit_encryption_mode = "required" # enforce TLS in prod
  snapshot_retention_days = 1          # daily snapshot for prod
  apply_immediately       = false      # wait for maintenance window in prod
  tags                    = local.common_tags
}

# ── RDS ───────────────────────────────────────────────────────────────────────
module "rds" {
  source                = "../../modules/rds"
  name                  = local.name
  private_subnet_ids    = module.vpc.private_subnet_ids
  rds_security_group_id = module.security_groups.rds_sg_id
  instance_class        = "db.t3.small"
  allocated_storage_gb  = 20
  app_db_password       = var.app_db_password
  warehouse_db_password = var.warehouse_db_password

  # Prod: deletion protection on, 7-day backups
  multi_az                    = false
  skip_final_snapshot         = false
  deletion_protection         = true
  backup_retention_days       = 7
  enable_performance_insights = true

  tags = local.common_tags
}

# ── ALB + WAF ─────────────────────────────────────────────────────────────────
module "alb" {
  source                = "../../modules/alb"
  name                  = local.name
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.security_groups.alb_sg_id
  ec2_instance_id       = module.ec2.instance_id
  enable_https          = true # enforce TLS in prod
  acm_certificate_arn   = var.acm_certificate_arn
  enable_waf            = true
  tags                  = local.common_tags
}
