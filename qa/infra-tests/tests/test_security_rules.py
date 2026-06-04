"""
Validate that prod and dev Terraform configurations enforce the correct
security posture. These tests parse the HCL source files — no AWS credentials
or live resources required.

Rules enforced:
  Prod: no SSH, no public IP, HTTPS only, WAF on, RDS deletion protection on
  Dev:  SSH on, public IP on, HTTP only (no ACM cert), WAF off, fast teardown
"""

import pytest
from tf_helpers import has_setting, read_env, read_module

# ── Production security rules ─────────────────────────────────────────────────


class TestProdSecurity:
    @pytest.fixture(scope="class")
    def prod(self):
        return read_env("prod")

    def test_ssh_explicitly_disabled(self, prod):
        assert has_setting(prod, "enable_ssh", "false"), (
            "Prod must set enable_ssh = false"
            " — port 22 must never be open in production"
        )

    def test_ssh_never_enabled(self, prod):
        assert not has_setting(
            prod, "enable_ssh", "true"
        ), "Prod must never set enable_ssh = true"

    def test_no_public_compute(self, prod):
        assert "enable_public_ip" not in prod, (
            "Prod must not expose compute to the public internet"
            " — ECS Fargate tasks run in private subnets only"
        )

    def test_https_not_required(self, prod):
        assert has_setting(
            prod, "enable_https", "false"
        ), "Prod ALB uses HTTP-only (no ACM cert); WAF provides request filtering"

    def test_waf_enabled(self, prod):
        assert has_setting(
            prod, "enable_waf", "true"
        ), "Prod ALB must have WAF v2 enabled (OWASP rules + rate limiting)"

    def test_rds_deletion_protection(self, prod):
        assert has_setting(prod, "deletion_protection", "true"), (
            "Prod RDS must have deletion_protection = true"
            " to prevent accidental data loss"
        )

    def test_rds_backup_retention(self, prod):
        assert has_setting(
            prod, "backup_retention_days", "7"
        ), "Prod RDS must retain backups for at least 7 days"

    def test_s3_versioning_enabled(self, prod):
        assert has_setting(
            prod, "versioning_enabled", "true"
        ), "Prod S3 bucket must have versioning enabled for object recovery"

    def test_redis_tls_required(self, prod):
        assert has_setting(
            prod, "transit_encryption_mode", '"required"'
        ), "Prod Redis must require TLS in transit (no plaintext connections allowed)"

    def test_ecs_in_private_subnets(self, prod):
        assert (
            "private_subnet_ids" in prod
        ), "Prod ECS tasks must run in private subnets — no direct internet exposure"


# ── Dev / testing permissive rules ───────────────────────────────────────────


class TestDevAccess:
    @pytest.fixture(scope="class")
    def dev(self):
        return read_env("dev")

    def test_ssh_enabled_for_dev(self, dev):
        assert has_setting(
            dev, "enable_ssh", "true"
        ), "Dev must enable SSH so engineers can shell into EC2 for debugging"

    def test_public_ip_for_ssh(self, dev):
        assert has_setting(
            dev, "enable_public_ip", "true"
        ), "Dev EC2 must have a public IP so SSH key-based access works directly"

    def test_http_only_no_cert_required(self, dev):
        assert has_setting(
            dev, "enable_https", "false"
        ), "Dev ALB uses HTTP only — no ACM certificate required for testing"

    def test_no_waf_in_dev(self, dev):
        assert has_setting(
            dev, "enable_waf", "false"
        ), "Dev must not enable WAF — it adds cost and is not needed for testing"

    def test_no_deletion_protection_in_dev(self, dev):
        assert has_setting(dev, "deletion_protection", "false"), (
            "Dev RDS must not have deletion protection"
            " — allows fast teardown with terraform destroy"
        )

    def test_skip_final_snapshot_in_dev(self, dev):
        assert has_setting(
            dev, "skip_final_snapshot", "true"
        ), "Dev RDS must skip the final snapshot to allow clean teardown"

    def test_ec2_in_public_subnet(self, dev):
        assert (
            "public_subnet_a_id" in dev
        ), "Dev EC2 must be in a public subnet so SSH works via the public IP"

    def test_ssh_key_wired_up(self, dev):
        assert (
            "key_name" in dev
        ), "Dev EC2 must have key_name set — required for SSH authentication"


# ── Security group module hardening ──────────────────────────────────────────


class TestSecurityGroupModule:
    @pytest.fixture(scope="class")
    def sg_main(self):
        return read_module("security-groups")

    def test_ssh_rule_is_dynamic(self, sg_main):
        assert (
            "for_each = var.enable_ssh" in sg_main
        ), "SSH ingress rule must be inside a dynamic block gated by enable_ssh"

    def test_rds_only_from_ec2_sg(self, sg_main):
        assert (
            "security_groups = [aws_security_group.ec2.id]" in sg_main
        ), "RDS SG must restrict access to the EC2 SG only — no CIDR-based ingress"

    def test_redis_only_from_ec2_sg(self, sg_main):
        content = sg_main
        redis_block_start = content.find('sg-redis"')
        redis_section = content[redis_block_start:]
        assert (
            "security_groups = [aws_security_group.ec2.id]" in redis_section
        ), "Redis SG must restrict access to the EC2 SG only"


# ── EC2 module hardening ──────────────────────────────────────────────────────


class TestEC2Module:
    @pytest.fixture(scope="class")
    def ec2_main(self):
        return read_module("ec2")

    def test_imdsv2_required(self, ec2_main):
        assert (
            'http_tokens = "required"' in ec2_main
        ), "EC2 must require IMDSv2 (blocks SSRF-based metadata token theft)"

    def test_root_volume_encrypted(self, ec2_main):
        assert (
            "encrypted             = true" in ec2_main
        ), "EC2 root EBS volume must be encrypted at rest"

    def test_public_ip_controlled_by_variable(self, ec2_main):
        assert (
            "associate_public_ip_address = var.enable_public_ip" in ec2_main
        ), "Public IP assignment must be controlled by the enable_public_ip variable"


# ── VPC module networking ─────────────────────────────────────────────────────


class TestVPCModule:
    @pytest.fixture(scope="class")
    def vpc_main(self):
        return read_module("vpc")

    def test_dns_hostnames_enabled(self, vpc_main):
        assert "enable_dns_hostnames = true" in vpc_main, (
            "VPC must have DNS hostnames enabled"
            " — required for SSM and RDS endpoint resolution"
        )

    def test_dns_support_enabled(self, vpc_main):
        assert (
            "enable_dns_support   = true" in vpc_main
        ), "VPC must have DNS support enabled"

    def test_nat_gateway_uses_eip(self, vpc_main):
        assert (
            "aws_eip" in vpc_main and "aws_nat_gateway" in vpc_main
        ), "NAT Gateway must have an Elastic IP for stable outbound addressing"

    def test_private_subnet_routes_through_nat(self, vpc_main):
        assert (
            "nat_gateway_id = aws_nat_gateway.this.id" in vpc_main
        ), "Private subnets must route outbound traffic through the NAT Gateway"

    def test_public_subnet_routes_through_igw(self, vpc_main):
        assert (
            "gateway_id = aws_internet_gateway.this.id" in vpc_main
        ), "Public subnets must route to the Internet Gateway"
