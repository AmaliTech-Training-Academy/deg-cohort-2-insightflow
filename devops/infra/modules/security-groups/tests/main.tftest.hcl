# Terraform tests for the security-groups module.
# Run with: terraform test
# These use mock_provider so no AWS credentials are required.

mock_provider "aws" {}

# ── Prod mode: SSH must be completely absent ───────────────────────────────────

run "prod_mode_no_ssh_rule" {
  command = plan

  variables {
    name       = "insightflow-prod"
    vpc_id     = "vpc-00000000000000001"
    enable_alb = true
    enable_ssh = false
  }

  assert {
    condition     = !anytrue([for r in aws_security_group.ec2.ingress : r.from_port == 22])
    error_message = "Port 22 must not appear in EC2 ingress rules when enable_ssh = false"
  }

  assert {
    condition     = aws_security_group.ec2.name == "insightflow-prod-sg-ec2"
    error_message = "EC2 SG name must follow the <name>-sg-ec2 convention"
  }

  assert {
    condition     = aws_security_group.rds.name == "insightflow-prod-sg-rds"
    error_message = "RDS SG name must follow the <name>-sg-rds convention"
  }
}

# ── Dev mode: SSH rule must be present with correct CIDR ──────────────────────

run "dev_mode_ssh_rule_present" {
  command = plan

  variables {
    name            = "insightflow-dev"
    vpc_id          = "vpc-00000000000000002"
    enable_alb      = true
    enable_ssh      = true
    ssh_cidr_blocks = ["10.0.0.0/8"]
  }

  assert {
    condition     = anytrue([for r in aws_security_group.ec2.ingress : r.from_port == 22])
    error_message = "Port 22 must be present in EC2 ingress rules when enable_ssh = true"
  }

  assert {
    condition = anytrue([
      for r in aws_security_group.ec2.ingress :
      r.from_port == 22 && contains(r.cidr_blocks, "10.0.0.0/8")
    ])
    error_message = "SSH rule must restrict access to the provided ssh_cidr_blocks"
  }
}

# ── RDS is always locked to EC2 SG — never open to internet ──────────────────

run "rds_only_reachable_from_ec2" {
  command = plan

  variables {
    name       = "insightflow-test"
    vpc_id     = "vpc-00000000000000003"
    enable_alb = true
    enable_ssh = false
  }

  assert {
    condition     = length(aws_security_group.rds.ingress) == 1
    error_message = "RDS SG must have exactly one ingress rule (from EC2 SG only)"
  }

  assert {
    condition     = alltrue([for r in aws_security_group.rds.ingress : r.from_port == 5432])
    error_message = "RDS SG ingress must only allow port 5432"
  }

  assert {
    condition     = alltrue([for r in aws_security_group.rds.ingress : length(r.cidr_blocks) == 0])
    error_message = "RDS SG must not have any CIDR-based ingress (SG-to-SG only)"
  }
}
