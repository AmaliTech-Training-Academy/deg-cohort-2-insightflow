output "dev_role_arn" {
  description = "Add this as GitHub Secret AWS_DEPLOY_ROLE_DEV"
  value       = aws_iam_role.github_deploy_dev.arn
}

output "prod_role_arn" {
  description = "Add this as GitHub Secret AWS_DEPLOY_ROLE_PROD"
  value       = aws_iam_role.github_deploy_prod.arn
}

