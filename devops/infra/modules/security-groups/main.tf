terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# ── ALB — accepts HTTP/HTTPS from the internet ────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "${var.name}-sg-alb"
  description = "ALB: inbound 80/443 from internet, outbound to compute"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Forward to compute layer"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-alb" })
}

# ── EC2 — inbound from ALB; SSH only if explicitly enabled (dev only) ─────────
resource "aws_security_group" "ec2" {
  name        = "${var.name}-sg-ec2"
  description = "EC2: inbound from ALB${var.enable_ssh ? ", SSH for dev" : " only"}"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = var.enable_alb ? [aws_security_group.alb.id] : []
  }

  ingress {
    description     = "Django API from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = var.enable_alb ? [aws_security_group.alb.id] : []
  }

  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []
    content {
      description = "SSH — dev only, never open in prod"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.ssh_cidr_blocks
    }
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-ec2" })
}

# ── ECS tasks — inbound from ALB; outbound to DBs, ECR, Secrets Manager ───────
# Only created when enable_ecs = true (i.e. prod ECS environment).
# In dev, docker compose runs on EC2 so the EC2 SG is used instead.
resource "aws_security_group" "ecs" {
  count = var.enable_ecs ? 1 : 0

  name        = "${var.name}-sg-ecs"
  description = "ECS Fargate tasks: inbound from ALB, outbound to VPC and internet"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Django API from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "All outbound via NAT GW to ECR, Secrets Manager, CloudWatch"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-ecs" })
}

# ── RDS — accepts DB connections from EC2 (dev) and/or ECS tasks (prod) ───────
resource "aws_security_group" "rds" {
  name        = "${var.name}-sg-rds"
  description = "RDS PostgreSQL: inbound 5432 from compute layer only"
  vpc_id      = var.vpc_id

  # Dev: Docker Compose on EC2 connects directly
  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  # Prod: ECS Fargate tasks connect to RDS
  dynamic "ingress" {
    for_each = var.enable_ecs ? [1] : []
    content {
      description     = "PostgreSQL from ECS tasks"
      from_port       = 5432
      to_port         = 5432
      protocol        = "tcp"
      security_groups = [aws_security_group.ecs[0].id]
    }
  }

  # Dev direct access — never enable in prod
  dynamic "ingress" {
    for_each = var.allow_public_db_access ? [1] : []
    content {
      description = "PostgreSQL public access — dev only"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = var.db_public_cidr_blocks
    }
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-rds" })
}

# ── Redis (ElastiCache) — accepts connections from EC2 (dev) and ECS (prod) ───
resource "aws_security_group" "redis" {
  name        = "${var.name}-sg-redis"
  description = "ElastiCache Redis: inbound 6379 from compute layer only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EC2"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  dynamic "ingress" {
    for_each = var.enable_ecs ? [1] : []
    content {
      description     = "Redis from ECS tasks"
      from_port       = 6379
      to_port         = 6379
      protocol        = "tcp"
      security_groups = [aws_security_group.ecs[0].id]
    }
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-redis" })
}
