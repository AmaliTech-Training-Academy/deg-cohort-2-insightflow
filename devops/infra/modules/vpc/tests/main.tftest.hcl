# Terraform tests for the vpc module.
# Run with: terraform test
# These use mock_provider so no AWS credentials are required.

mock_provider "aws" {}

variables {
  name           = "insightflow-test"
  region         = "eu-west-1"
  vpc_cidr       = "10.99.0.0/16"
  public_cidr_a  = "10.99.1.0/24"
  public_cidr_b  = "10.99.2.0/24"
  private_cidr_a = "10.99.10.0/24"
  private_cidr_b = "10.99.11.0/24"
}

# ── VPC CIDR must match the input ─────────────────────────────────────────────

run "vpc_cidr_matches_variable" {
  command = plan

  assert {
    condition     = aws_vpc.this.cidr_block == "10.99.0.0/16"
    error_message = "VPC CIDR block must match the vpc_cidr variable"
  }

  assert {
    condition     = aws_vpc.this.enable_dns_hostnames == true
    error_message = "DNS hostnames must be enabled (required for SSM and RDS endpoint resolution)"
  }

  assert {
    condition     = aws_vpc.this.enable_dns_support == true
    error_message = "DNS support must be enabled"
  }
}

# ── Subnets must land in the correct AZs ──────────────────────────────────────

run "subnets_in_correct_availability_zones" {
  command = plan

  assert {
    condition     = aws_subnet.public_a.availability_zone == "eu-west-1a"
    error_message = "Public subnet A must be in eu-west-1a"
  }

  assert {
    condition     = aws_subnet.public_b.availability_zone == "eu-west-1b"
    error_message = "Public subnet B must be in eu-west-1b"
  }

  assert {
    condition     = aws_subnet.private_a.availability_zone == "eu-west-1a"
    error_message = "Private subnet A must be in eu-west-1a"
  }

  assert {
    condition     = aws_subnet.private_b.availability_zone == "eu-west-1b"
    error_message = "Private subnet B must be in eu-west-1b"
  }
}

# ── Subnet CIDRs must match the inputs ────────────────────────────────────────

run "subnet_cidrs_match_variables" {
  command = plan

  assert {
    condition     = aws_subnet.public_a.cidr_block == "10.99.1.0/24"
    error_message = "Public subnet A CIDR must match public_cidr_a"
  }

  assert {
    condition     = aws_subnet.private_a.cidr_block == "10.99.10.0/24"
    error_message = "Private subnet A CIDR must match private_cidr_a"
  }
}

# ── Public subnets must NOT auto-assign IPs (EC2 module controls this) ────────

run "public_subnets_no_auto_assign_ip" {
  command = plan

  assert {
    condition     = aws_subnet.public_a.map_public_ip_on_launch == false
    error_message = "Public subnet A must not auto-assign IPs — EC2 module sets this explicitly"
  }

  assert {
    condition     = aws_subnet.public_b.map_public_ip_on_launch == false
    error_message = "Public subnet B must not auto-assign IPs"
  }
}

# ── NAT Gateway must be in a public subnet ────────────────────────────────────

run "nat_gateway_in_public_subnet" {
  command = plan

  assert {
    condition     = aws_nat_gateway.this.subnet_id == aws_subnet.public_a.id
    error_message = "NAT Gateway must be placed in the public subnet (not private)"
  }
}
