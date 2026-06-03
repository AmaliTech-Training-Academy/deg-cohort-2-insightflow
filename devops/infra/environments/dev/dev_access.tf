# ── Developer tunnel access ───────────────────────────────────────────────────
# Gives a developer AWS credentials that ONLY allow SSM port-forwarding to the
# dev EC2 instance. No console access, no S3, no RDS direct access.
# Usage: create one IAM user per developer, attach this policy.

resource "aws_iam_policy" "dev_tunnel" {
  name        = "${local.name}-dev-tunnel"
  description = "Allows SSM port-forwarding to the dev EC2 only — no other AWS access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMPortForwardToDevEC2"
        Effect = "Allow"
        Action = [
          "ssm:StartSession",
          "ssm:TerminateSession",
          "ssm:ResumeSession",
          "ssm:DescribeSessions",
          "ssm:GetConnectionStatus"
        ]
        Resource = [
          "arn:aws:ec2:${var.region}:${data.aws_caller_identity.current.account_id}:instance/${module.ec2.instance_id}",
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:session/$${aws:username}-*",
          "arn:aws:ssm:*::document/AWS-StartPortForwardingSessionToRemoteHost"
        ]
      }
    ]
  })

  tags = local.common_tags
}

# Create one user per developer — share their access key securely (not Slack/email)
resource "aws_iam_user" "developers" {
  for_each = toset(var.developer_usernames)
  name     = each.key
  tags     = local.common_tags
}

resource "aws_iam_user_policy_attachment" "dev_tunnel" {
  for_each   = aws_iam_user.developers
  user       = each.value.name
  policy_arn = aws_iam_policy.dev_tunnel.arn
}

resource "aws_iam_access_key" "developers" {
  for_each = aws_iam_user.developers
  user     = each.value.name
}

output "developer_credentials" {
  description = "Share each credential SECURELY (not Slack). Run: terraform output -json developer_credentials"
  sensitive   = true
  value = {
    for username, key in aws_iam_access_key.developers : username => {
      access_key_id     = key.id
      secret_access_key = key.secret
      region            = var.region
    }
  }
}
