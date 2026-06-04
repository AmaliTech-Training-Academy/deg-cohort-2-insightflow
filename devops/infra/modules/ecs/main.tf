terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

data "aws_caller_identity" "current" {}

# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "this" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

# ── CloudWatch Log Groups ─────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.name}/backend"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.name}/frontend"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/ecs/${var.name}/celery-worker"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "etl" {
  name              = "/ecs/${var.name}/etl"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# ── Security group ────────────────────────────────────────────────────────────
# The ECS tasks SG is created by the security-groups module (enable_ecs = true)
# and passed in via var.tasks_sg_id. This keeps all SG rules in one place and
# avoids circular dependencies between modules.

# ── IAM — Task Execution Role (ECS control plane) ────────────────────────────
resource "aws_iam_role" "execution" {
  name = "${var.name}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name}-ecs-execution-secrets"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ]
      Resource = [
        var.app_db_secret_arn,
        var.warehouse_db_secret_arn,
        var.redis_secret_arn,
      ]
    }]
  })
}

# ── IAM — Task Role (app permissions) ────────────────────────────────────────
resource "aws_iam_role" "task" {
  name = "${var.name}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "task" {
  name = "${var.name}-ecs-task-policy"
  role = aws_iam_role.task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Media"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.backend.arn}:*",
          "${aws_cloudwatch_log_group.frontend.arn}:*",
          "${aws_cloudwatch_log_group.celery.arn}:*",
          "${aws_cloudwatch_log_group.etl.arn}:*",
        ]
      },
      {
        Sid    = "SecretsRead"
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = [
          var.app_db_secret_arn,
          var.warehouse_db_secret_arn,
          var.redis_secret_arn,
        ]
      }
    ]
  })
}

# ── ALB Target Groups (IP-based for Fargate) ──────────────────────────────────
resource "aws_lb_target_group" "backend" {
  name        = "${var.name}-backend"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/api-docs/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }

  tags = var.tags
}

resource "aws_lb_target_group" "frontend" {
  name        = "${var.name}-frontend"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }

  tags = var.tags
}

# ── ALB Listener Rules ────────────────────────────────────────────────────────
resource "aws_lb_listener_rule" "api" {
  listener_arn = var.alb_listener_arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/api-docs/*", "/admin/*"]
    }
  }
}

resource "aws_lb_listener_rule" "frontend" {
  listener_arn = var.alb_listener_arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }

  condition {
    path_pattern {
      values = ["/*"]
    }
  }
}

# ── Task Definitions ──────────────────────────────────────────────────────────
locals {
  log_config_backend = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.backend.name
      "awslogs-region"        = var.region
      "awslogs-stream-prefix" = "backend"
    }
  }
  log_config_frontend = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
      "awslogs-region"        = var.region
      "awslogs-stream-prefix" = "frontend"
    }
  }
  log_config_celery = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.celery.name
      "awslogs-region"        = var.region
      "awslogs-stream-prefix" = "celery"
    }
  }
  log_config_etl = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = aws_cloudwatch_log_group.etl.name
      "awslogs-region"        = var.region
      "awslogs-stream-prefix" = "etl"
    }
  }

  # Secrets injected from Secrets Manager into containers
  db_secrets = [
    { name = "DB_HOST", valueFrom = "${var.app_db_secret_arn}:host::" },
    { name = "DB_NAME", valueFrom = "${var.app_db_secret_arn}:dbname::" },
    { name = "DB_USER", valueFrom = "${var.app_db_secret_arn}:username::" },
    { name = "DB_PASSWORD", valueFrom = "${var.app_db_secret_arn}:password::" },
    { name = "DJANGO_SECRET_KEY", valueFrom = "${var.app_db_secret_arn}:django_secret_key::" },
  ]

  warehouse_secrets = [
    { name = "WAREHOUSE_DB_HOST", valueFrom = "${var.warehouse_db_secret_arn}:host::" },
    { name = "WAREHOUSE_DB_NAME", valueFrom = "${var.warehouse_db_secret_arn}:dbname::" },
    { name = "WAREHOUSE_DB_USER", valueFrom = "${var.warehouse_db_secret_arn}:username::" },
    { name = "WAREHOUSE_DB_PASSWORD", valueFrom = "${var.warehouse_db_secret_arn}:password::" },
  ]

  redis_secrets = [
    { name = "REDIS_URL", valueFrom = "${var.redis_secret_arn}:url::" },
  ]

  backend_env = [
    { name = "DJANGO_SETTINGS_MODULE", value = var.django_settings_module },
    { name = "DEBUG", value = "False" },
    { name = "DB_PORT", value = "5432" },
    { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
    { name = "CORS_ALLOWED_ORIGINS", value = var.cors_allowed_origins },
    { name = "SECURE_SSL_REDIRECT", value = "True" },
    { name = "MEDIA_ROOT", value = "/tmp/media" },
    { name = "AWS_S3_BUCKET", value = var.s3_bucket_name },
  ]
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name             = "backend"
    image            = var.backend_image
    essential        = true
    portMappings     = [{ containerPort = 8080, protocol = "tcp" }]
    environment      = local.backend_env
    secrets          = concat(local.db_secrets, local.redis_secrets)
    logConfiguration = local.log_config_backend
    command = ["sh", "-c",
      "python manage.py migrate && python manage.py seed_data && gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout 120 insightflow.wsgi:application"
    ]
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "migration" {
  family                   = "${var.name}-migration"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name                   = "migration"
    image                  = var.backend_image
    essential              = true
    readonlyRootFilesystem = true
    environment            = local.backend_env
    secrets                = local.db_secrets
    logConfiguration       = local.log_config_backend
    command                = ["python", "manage.py", "migrate", "--noinput"]
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "celery" {
  family                   = "${var.name}-celery-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name             = "celery-worker"
    image            = var.backend_image
    essential        = true
    environment      = local.backend_env
    secrets          = concat(local.db_secrets, local.redis_secrets)
    logConfiguration = local.log_config_celery
    command          = ["celery", "-A", "insightflow", "worker", "--loglevel=info", "--concurrency=2"]
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name                   = "frontend"
    image                  = var.frontend_image
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 3000, protocol = "tcp" }]
    environment            = []
    secrets                = []
    logConfiguration       = local.log_config_frontend
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "etl" {
  family                   = "${var.name}-etl"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "etl"
    image     = var.etl_image
    essential = true
    environment = [
      { name = "DB_PORT", value = "5432" },
      { name = "WAREHOUSE_DB_PORT", value = "5432" },
      { name = "ETL_BATCH_SIZE", value = "1000" },
    ]
    secrets          = concat(local.db_secrets, local.warehouse_secrets, local.redis_secrets)
    logConfiguration = local.log_config_etl
    command          = ["sh", "-c", "python create_star_schema.py && python etl_pipeline.py"]
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "etl_listener" {
  family                   = "${var.name}-etl-listener"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "etl-listener"
    image     = var.etl_image
    essential = true
    environment = [
      { name = "DB_PORT", value = "5432" },
      { name = "ETL_DEBOUNCE_SECONDS", value = "300" },
    ]
    secrets          = concat(local.db_secrets, local.redis_secrets)
    logConfiguration = local.log_config_etl
    command          = ["sh", "-c", "python trigger_setup.py install && python -m etl.listener"]
  }])

  tags = var.tags
}

resource "aws_ecs_task_definition" "etl_worker" {
  family                   = "${var.name}-etl-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "etl-worker"
    image     = var.etl_image
    essential = true
    environment = [
      { name = "WAREHOUSE_DB_PORT", value = "5432" },
    ]
    secrets          = concat(local.warehouse_secrets, local.redis_secrets)
    logConfiguration = local.log_config_etl
    command          = ["celery", "-A", "celery_app", "worker", "--loglevel=info", "--queues=etl", "--concurrency=1"]
  }])

  tags = var.tags
}

# ── ECS Services ──────────────────────────────────────────────────────────────
resource "aws_ecs_service" "backend" {
  name                              = "${var.name}-backend"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.backend.arn
  desired_count                     = 1
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 120

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.tasks_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8080
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.tags
}

resource "aws_ecs_service" "frontend" {
  name                              = "${var.name}-frontend"
  cluster                           = aws_ecs_cluster.this.id
  task_definition                   = aws_ecs_task_definition.frontend.arn
  desired_count                     = 1
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.tasks_sg_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.tags
}

resource "aws_ecs_service" "celery" {
  name            = "${var.name}-celery-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.celery.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.tasks_sg_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.tags
}

resource "aws_ecs_service" "etl_listener" {
  name            = "${var.name}-etl-listener"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.etl_listener.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.tasks_sg_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.tags
}

resource "aws_ecs_service" "etl_worker" {
  name            = "${var.name}-etl-worker"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.etl_worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.tasks_sg_id]
    assign_public_ip = false
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = var.tags
}
