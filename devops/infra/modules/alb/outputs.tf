output "alb_dns_name" {
  description = "Point your domain's CNAME/ALIAS record here"
  value       = aws_lb.this.dns_name
}

output "alb_arn" {
  value = aws_lb.this.arn
}

output "http_listener_arn" {
  description = "HTTP listener ARN — passed to the ECS module to attach target group rules"
  value       = aws_lb_listener.http.arn
}

output "https_listener_arn" {
  value = var.enable_https ? aws_lb_listener.https[0].arn : null
}
