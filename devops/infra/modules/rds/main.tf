terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

# Subnet group must span ≥2 AZs — AWS requirement for all RDS instances
resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-rds-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.name}-rds-subnet-group" })
}

resource "aws_db_parameter_group" "postgres16" {
  name   = "${var.name}-pg16"
  family = "postgres16"
  tags   = var.tags
}

# IAM role for enhanced monitoring — only created when monitoring_interval > 0
resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  name  = "${var.name}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count      = var.monitoring_interval > 0 ? 1 : 0
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# App DB — OLTP (Django backend)
resource "aws_db_instance" "app" {
  identifier        = "${var.name}-app-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "insightflow_app"
  username = "insightflow"
  password = var.app_db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_security_group_id]
  parameter_group_name   = aws_db_parameter_group.postgres16.name

  multi_az                = var.multi_az
  publicly_accessible     = false
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection
  backup_retention_period = var.backup_retention_days

  auto_minor_version_upgrade          = true
  copy_tags_to_snapshot               = true
  iam_database_authentication_enabled = true
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]

  performance_insights_enabled = var.enable_performance_insights
  monitoring_interval          = var.monitoring_interval
  monitoring_role_arn          = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  tags = merge(var.tags, { Name = "${var.name}-app-db" })
}

# Warehouse DB — OLAP (ETL target, Streamlit source)
resource "aws_db_instance" "warehouse" {
  identifier        = "${var.name}-warehouse-db"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage_gb
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "insightflow_warehouse"
  username = "insightflow_wh"
  password = var.warehouse_db_password

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_security_group_id]
  parameter_group_name   = aws_db_parameter_group.postgres16.name

  multi_az                = var.multi_az
  publicly_accessible     = false
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = var.deletion_protection
  backup_retention_period = var.backup_retention_days

  auto_minor_version_upgrade          = true
  copy_tags_to_snapshot               = true
  iam_database_authentication_enabled = true
  enabled_cloudwatch_logs_exports     = ["postgresql", "upgrade"]

  performance_insights_enabled = var.enable_performance_insights
  monitoring_interval          = var.monitoring_interval
  monitoring_role_arn          = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null

  tags = merge(var.tags, { Name = "${var.name}-warehouse-db" })
}

# Store DB credentials in Secrets Manager so EC2 never has plaintext passwords
resource "aws_secretsmanager_secret" "app_db" {
  name                    = "${var.name}/db/app"
  recovery_window_in_days = var.skip_final_snapshot ? 0 : 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "app_db" {
  secret_id = aws_secretsmanager_secret.app_db.id
  secret_string = jsonencode({
    host     = aws_db_instance.app.address
    port     = aws_db_instance.app.port
    dbname   = aws_db_instance.app.db_name
    username = aws_db_instance.app.username
    password = var.app_db_password
  })
}

resource "aws_secretsmanager_secret" "warehouse_db" {
  name                    = "${var.name}/db/warehouse"
  recovery_window_in_days = var.skip_final_snapshot ? 0 : 7
  tags                    = var.tags
}

resource "aws_secretsmanager_secret_version" "warehouse_db" {
  secret_id = aws_secretsmanager_secret.warehouse_db.id
  secret_string = jsonencode({
    host     = aws_db_instance.warehouse.address
    port     = aws_db_instance.warehouse.port
    dbname   = aws_db_instance.warehouse.db_name
    username = aws_db_instance.warehouse.username
    password = var.warehouse_db_password
  })
}
