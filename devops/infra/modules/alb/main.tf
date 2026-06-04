terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

resource "aws_lb" "this" {
  name               = "${var.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  drop_invalid_header_fields = true
  enable_deletion_protection = var.enable_deletion_protection

  dynamic "access_logs" {
    for_each = var.access_logs_bucket != "" ? [1] : []
    content {
      bucket  = var.access_logs_bucket
      prefix  = "${var.name}-alb"
      enabled = true
    }
  }

  tags = merge(var.tags, { Name = "${var.name}-alb" })
}

# ── Target groups (EC2 mode only) ─────────────────────────────────────────────
# When ec2_instance_id is empty the ALB is used with ECS.
# In ECS mode the ECS module creates IP-based target groups and listener rules;
# these instance-based groups are not created at all.

resource "aws_lb_target_group" "frontend" {
  count = var.ec2_instance_id != "" ? 1 : 0

  name        = "${var.name}-tg-frontend"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = var.tags
}

resource "aws_lb_target_group" "api" {
  count = var.ec2_instance_id != "" ? 1 : 0

  name        = "${var.name}-tg-api"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "instance"

  health_check {
    path                = "/api-docs/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = var.tags
}

resource "aws_lb_target_group_attachment" "frontend" {
  count = var.ec2_instance_id != "" ? 1 : 0

  target_group_arn = aws_lb_target_group.frontend[0].arn
  target_id        = var.ec2_instance_id
  port             = 3000
}

resource "aws_lb_target_group_attachment" "api" {
  count = var.ec2_instance_id != "" ? 1 : 0

  target_group_arn = aws_lb_target_group.api[0].arn
  target_id        = var.ec2_instance_id
  port             = 8080
}

# ── Listeners ─────────────────────────────────────────────────────────────────

locals {
  # Which ARN the API listener rule attaches to (HTTPS when enabled, else HTTP)
  main_listener_arn = var.enable_https ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  # Case 1 — HTTPS mode: redirect port 80 to 443
  dynamic "default_action" {
    for_each = var.enable_https ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }

  # Case 2 — EC2 mode: forward to EC2-backed frontend target group
  dynamic "default_action" {
    for_each = !var.enable_https && var.ec2_instance_id != "" ? [1] : []
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.frontend[0].arn
    }
  }

  # Case 3 — ECS mode: fixed 503; ECS listener rules (/* at priority 20) take over
  dynamic "default_action" {
    for_each = !var.enable_https && var.ec2_instance_id == "" ? [1] : []
    content {
      type = "fixed-response"
      fixed_response {
        content_type = "text/plain"
        message_body = "Service unavailable"
        status_code  = "503"
      }
    }
  }
}

resource "aws_lb_listener" "https" {
  count = var.enable_https ? 1 : 0

  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend[0].arn
  }
}

# /api/* and /api-docs/* → Django (EC2 mode only; ECS module creates its own rules)
resource "aws_lb_listener_rule" "api" {
  count = var.ec2_instance_id != "" ? 1 : 0

  listener_arn = local.main_listener_arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/api-docs/*", "/swagger-ui/*", "/admin/*"]
    }
  }
}

# ── WAF v2 ────────────────────────────────────────────────────────────────────

resource "aws_wafv2_web_acl" "this" {
  count = var.enable_waf ? 1 : 0

  name  = "${var.name}-waf"
  scope = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimit"
    priority = 3
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.name}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.name}-waf"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

resource "aws_wafv2_web_acl_association" "alb" {
  count        = var.enable_waf ? 1 : 0
  resource_arn = aws_lb.this.arn
  web_acl_arn  = aws_wafv2_web_acl.this[0].arn
}

resource "aws_cloudwatch_log_group" "waf" {
  count             = var.enable_waf ? 1 : 0
  name              = "aws-waf-logs-${var.name}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_wafv2_web_acl_logging_configuration" "this" {
  count                   = var.enable_waf ? 1 : 0
  log_destination_configs = [aws_cloudwatch_log_group.waf[0].arn]
  resource_arn            = aws_wafv2_web_acl.this[0].arn
}
