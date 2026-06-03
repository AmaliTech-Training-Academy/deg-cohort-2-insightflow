terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  # Uncomment after creating the S3 bucket + DynamoDB table
  # backend "s3" {
  #   bucket         = "insightflow-tfstate"
  #   key            = "github-oidc/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "insightflow-tfstate-lock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project   = "InsightFlow"
      ManagedBy = "terraform"
      Purpose   = "github-oidc"
    }
  }
}

data "aws_caller_identity" "current" {}

# ── GitHub OIDC provider (already exists in this AWS account) ────────────────
# Look it up rather than create it — the provider is account-global and may
# have been created by another team or tool.
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

locals {
  repo      = "${var.github_org}/${var.github_repo}"
  oidc_arn  = data.aws_iam_openid_connect_provider.github.arn
  oidc_host = "token.actions.githubusercontent.com"
}

# ── Dev deploy role ───────────────────────────────────────────────────────────
# Used by deploy-dev.yml — SSM deploy only, no Terraform.
# Scoped to the dev branch.
resource "aws_iam_role" "github_deploy_dev" {
  name        = "insightflow-github-deploy-dev"
  description = "GitHub Actions deploy role for dev branch - SSM only"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "${local.oidc_host}:sub" = "repo:${local.repo}:ref:refs/heads/dev"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy_dev" {
  #checkov:skip=CKV_AWS_355:SSM describe/list and CloudWatch actions cannot be scoped below account level
  #checkov:skip=CKV_AWS_290:ssm:SendCommand is scoped to account instances; no further restriction possible without known instance IDs
  name = "insightflow-deploy-dev"
  role = aws_iam_role.github_deploy_dev.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMSendCommand"
        Effect = "Allow"
        Action = ["ssm:SendCommand"]
        Resource = [
          "arn:aws:ec2:*:${data.aws_caller_identity.current.account_id}:instance/*",
          "arn:aws:ssm:*:${data.aws_caller_identity.current.account_id}:document/AWS-RunShellScript"
        ]
      },
      {
        Sid    = "SSMReadCommand"
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation",
          "ssm:ListCommandInvocations"
        ]
        Resource = "*"
      },
      {
        Sid      = "EC2Describe"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
      {
        Sid      = "CloudWatchMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
      }
    ]
  })
}

# ── Prod deploy role ──────────────────────────────────────────────────────────
# Used by deploy-prod.yml — Terraform plan/apply + SSM deploy.
# Scoped to the main branch.
resource "aws_iam_role" "github_deploy_prod" {
  name        = "insightflow-github-deploy-prod"
  description = "GitHub Actions deploy role for prod (main) branch - Terraform + SSM"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = local.oidc_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${local.oidc_host}:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "${local.oidc_host}:sub" = "repo:${local.repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy_prod" {
  #checkov:skip=CKV_AWS_355:Terraform deploy role requires broad resource scope; ARNs are unknown at role creation time
  #checkov:skip=CKV_AWS_290:Write access is intentional — role manages all prod infrastructure via Terraform
  #checkov:skip=CKV_AWS_286:iam:PassRole is required for Terraform to attach roles to EC2 instances
  #checkov:skip=CKV_AWS_287:secretsmanager access is scoped to insightflow-prod/* namespace only
  #checkov:skip=CKV_AWS_288:s3 and secretsmanager access is required for Terraform state and app secrets
  #checkov:skip=CKV_AWS_289:IAM permissions management is required for Terraform to create EC2 and VPC roles
  name = "insightflow-deploy-prod"
  role = aws_iam_role.github_deploy_prod.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ── SSM (same as dev) ───────────────────────────────────────────────────
      {
        Sid    = "SSMRunCommand"
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:DescribeInstanceInformation",
          "ssm:ListCommandInvocations"
        ]
        Resource = "*"
      },
      {
        Sid      = "EC2Describe"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
      # ── CloudWatch + Logs (metrics and deployment events) ───────────────────
      {
        Sid    = "CloudWatch"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      },
      # ── Terraform — compute & network ───────────────────────────────────────
      {
        Sid      = "EC2Full"
        Effect   = "Allow"
        Action   = ["ec2:*"]
        Resource = "*"
      },
      {
        Sid      = "VPCFull"
        Effect   = "Allow"
        Action   = ["vpc:*"]
        Resource = "*"
      },
      # ── Terraform — database & cache ────────────────────────────────────────
      {
        Sid      = "RDSFull"
        Effect   = "Allow"
        Action   = ["rds:*"]
        Resource = "*"
      },
      {
        Sid      = "ElastiCacheFull"
        Effect   = "Allow"
        Action   = ["elasticache:*"]
        Resource = "*"
      },
      # ── Terraform — load balancer & WAF ─────────────────────────────────────
      {
        Sid      = "ALBFull"
        Effect   = "Allow"
        Action   = ["elasticloadbalancing:*"]
        Resource = "*"
      },
      {
        Sid      = "WAFv2Full"
        Effect   = "Allow"
        Action   = ["wafv2:*"]
        Resource = "*"
      },
      # ── Terraform — storage ─────────────────────────────────────────────────
      {
        Sid      = "S3Full"
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = "*"
      },
      # ── Terraform — IAM roles created for EC2 and VPC flow logs ─────────────
      {
        Sid    = "IAMForTerraform"
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PassRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:CreateInstanceProfile",
          "iam:DeleteInstanceProfile",
          "iam:AddRoleToInstanceProfile",
          "iam:RemoveRoleFromInstanceProfile",
          "iam:GetInstanceProfile",
          "iam:ListInstanceProfilesForRole",
          "iam:TagRole",
          "iam:UntagRole"
        ]
        Resource = "*"
      },
      # ── Terraform — secrets (prod namespace only) ────────────────────────────
      {
        Sid      = "SecretsManager"
        Effect   = "Allow"
        Action   = ["secretsmanager:*"]
        Resource = "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:insightflow-prod/*"
      },
      # ── Terraform — ACM cert (read-only; cert is pre-provisioned) ───────────
      {
        Sid    = "ACMReadOnly"
        Effect = "Allow"
        Action = [
          "acm:DescribeCertificate",
          "acm:GetCertificate",
          "acm:ListCertificates",
          "acm:ListTagsForCertificate"
        ]
        Resource = "*"
      },
      # ── Terraform state backend ─────────────────────────────────────────────
      {
        Sid    = "TerraformStateS3"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::insightflow-tfstate",
          "arn:aws:s3:::insightflow-tfstate/*"
        ]
      },
      {
        Sid    = "TerraformStateLock"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:DescribeTable"
        ]
        Resource = "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/insightflow-tfstate-lock"
      }
    ]
  })
}
