output "alb_sg_id" {
  value = aws_security_group.alb.id
}

output "ec2_sg_id" {
  value = aws_security_group.ec2.id
}

output "ecs_sg_id" {
  description = "Security group for ECS Fargate tasks. Null when enable_ecs = false."
  value       = var.enable_ecs ? aws_security_group.ecs[0].id : null
}

output "rds_sg_id" {
  value = aws_security_group.rds.id
}

output "redis_sg_id" {
  value = aws_security_group.redis.id
}
