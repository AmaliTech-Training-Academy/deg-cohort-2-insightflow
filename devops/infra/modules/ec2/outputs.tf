output "instance_id" {
  value = aws_instance.this.id
}

output "private_ip" {
  value = aws_instance.this.private_ip
}

output "public_ip" {
  description = "Public IP for SSH in dev. Empty string in prod (enable_public_ip = false)."
  value       = aws_instance.this.public_ip
}

output "iam_role_name" {
  value = aws_iam_role.ec2.name
}
