terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# ALB — accepts HTTPS/HTTP from the internet
resource "aws_security_group" "alb" {
  name        = "${var.name}-sg-alb"
  description = "ALB: inbound 80/443 from internet"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP (redirected to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Forward to EC2"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.name}-sg-alb" })
}

# EC2 — inbound from ALB; SSH only if explicitly enabled (dev/testing only)
resource "aws_security_group" "ec2" {
  name        = "${var.name}-sg-ec2"
  description = "EC2: inbound from ALB${var.enable_ssh ? ", SSH for dev/testing" : " only - no port 22"}"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Frontend from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = var.enable_alb ? [aws_security_group.alb.id] : []
    cidr_blocks     = var.enable_alb ? [] : []
  }

  ingress {
    description     = "Django API from ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = var.enable_alb ? [aws_security_group.alb.id] : []
    cidr_blocks     = var.enable_alb ? [] : []
  }

  # SSH — dev/testing only; never open in production
  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []
    content {
      description = "SSH - dev/testing only"
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

# RDS — accepts DB connections from EC2 only
resource "aws_security_group" "rds" {
  name        = "${var.name}-sg-rds"
  description = "RDS: inbound 5432 from EC2 only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  # Direct internet access — dev only; never enable in prod
  dynamic "ingress" {
    for_each = var.allow_public_db_access ? [1] : []
    content {
      description = "PostgreSQL public access - dev only"
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

# Redis (ElastiCache) — accepts connections from EC2 only
resource "aws_security_group" "redis" {
  name        = "${var.name}-sg-redis"
  description = "ElastiCache Redis: inbound 6379 from EC2 only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EC2"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
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
