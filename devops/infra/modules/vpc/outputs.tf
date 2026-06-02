output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = [aws_subnet.public_a.id, aws_subnet.public_b.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "public_subnet_a_id" {
  description = "Primary public subnet (AZ-a) — used for dev EC2 with public IP + SSH"
  value       = aws_subnet.public_a.id
}

output "private_subnet_a_id" {
  description = "Primary private subnet (AZ-a) — used for prod EC2 (SSM-only, no public IP)"
  value       = aws_subnet.private_a.id
}
