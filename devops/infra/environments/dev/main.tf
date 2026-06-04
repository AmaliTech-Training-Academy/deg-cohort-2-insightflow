terraform {
  required_version = ">= 1.6"
  required_providers {
    aws   = { source = "hashicorp/aws", version = "~> 5.0" }
    tls   = { source = "hashicorp/tls", version = "~> 4.0" }
    local = { source = "hashicorp/local", version = "~> 2.0" }
  }

  # Uncomment after creating the S3 bucket + DynamoDB table (see bootstrap/)
  # backend "s3" {
  #   bucket         = "insightflow-tfstate"
  #   key            = "dev/terraform.tfstate"
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
  name         = "insightflow-dev"
  ssh_key_path = pathexpand("~/.ssh/insightflow-dev.pem")
  common_tags = {
    Project     = "InsightFlow"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ── SSH key pair ──────────────────────────────────────────────────────────────
# Terraform generates the key — private key is saved outside the repo.
resource "tls_private_key" "dev" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "dev" {
  key_name   = "${local.name}-key"
  public_key = tls_private_key.dev.public_key_openssh
  tags       = local.common_tags
}

# Written to ~/.ssh/insightflow-dev.pem — outside the repo, chmod 400
resource "local_sensitive_file" "private_key" {
  filename        = local.ssh_key_path
  content         = tls_private_key.dev.private_key_openssh
  file_permission = "0400"
}

# ── S3 ────────────────────────────────────────────────────────────────────────
module "s3" {
  source             = "../../modules/s3"
  bucket_name        = "${local.name}-uploads-${data.aws_caller_identity.current.account_id}"
  versioning_enabled = false
  tags               = local.common_tags
}

# ── Network ───────────────────────────────────────────────────────────────────
module "vpc" {
  source             = "../../modules/vpc"
  name               = local.name
  region             = var.region
  vpc_cidr           = "10.1.0.0/16"
  public_cidr_a      = "10.1.1.0/24"
  public_cidr_b      = "10.1.2.0/24"
  private_cidr_a     = "10.1.10.0/24"
  private_cidr_b     = "10.1.11.0/24"
  enable_nat_gateway = false # EC2 is in a public subnet; RDS/Redis only accept inbound
  tags               = local.common_tags
}

# ── Security groups ───────────────────────────────────────────────────────────
# Dev: ALB routes HTTP traffic; SSH open for debugging.
module "security_groups" {
  source                    = "../../modules/security-groups"
  name                      = local.name
  vpc_id                    = module.vpc.vpc_id
  enable_alb                = true
  enable_ssh                = true          # dev only — never enable in prod
  ssh_cidr_blocks           = ["0.0.0.0/0"] # restrict to your IP for extra safety
  allow_public_db_access    = true          # dev only — direct DB access without tunnel
  allow_public_redis_access = true          # dev only — troubleshooting; ElastiCache has no public IP, use SSH tunnel
  allow_redis_proxy         = true          # dev only — EC2 socat proxy on port 6380 → Redis:6379
  tags                      = local.common_tags
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
# Dev: public subnet + public IP + SSH key — direct shell access.
# Prod: private subnet, no public IP, SSM-only.
module "ec2" {
  source             = "../../modules/ec2"
  name               = local.name
  region             = var.region
  subnet_id          = module.vpc.public_subnet_a_id
  security_group_id  = module.security_groups.ec2_sg_id
  instance_type      = "t3.2xlarge"
  root_volume_gb     = 50
  enable_public_ip   = true
  key_name           = aws_key_pair.dev.key_name
  s3_bucket_name     = module.s3.bucket_name
  log_retention_days = 7
  tags               = local.common_tags
}

# ── ElastiCache Redis ─────────────────────────────────────────────────────────
module "redis" {
  source                  = "../../modules/elasticache"
  name                    = local.name
  private_subnet_ids      = module.vpc.private_subnet_ids
  redis_security_group_id = module.security_groups.redis_sg_id
  node_type               = "cache.t3.micro"
  snapshot_retention_days = 0
  apply_immediately       = true
  tags                    = local.common_tags
}

# ── RDS ───────────────────────────────────────────────────────────────────────
module "rds" {
  source                = "../../modules/rds"
  name                  = local.name
  private_subnet_ids    = concat(module.vpc.public_subnet_ids, module.vpc.private_subnet_ids) # include public subnets so RDS can get a public IP
  rds_security_group_id = module.security_groups.rds_sg_id
  instance_class        = "db.t3.micro"
  allocated_storage_gb  = 20
  app_db_password       = var.app_db_password
  warehouse_db_password = var.warehouse_db_password

  multi_az              = false
  skip_final_snapshot   = true
  deletion_protection   = false
  backup_retention_days = 1
  publicly_accessible   = true # dev only — direct connection without tunnel

  tags = local.common_tags
}

# ── ALB ───────────────────────────────────────────────────────────────────────
# Dev: HTTP only (no ACM cert). Prod: HTTPS + WAF.
module "alb" {
  source                = "../../modules/alb"
  name                  = local.name
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.security_groups.alb_sg_id
  ec2_instance_id       = module.ec2.instance_id
  enable_https          = false
  enable_waf            = false
  tags                  = local.common_tags
}
