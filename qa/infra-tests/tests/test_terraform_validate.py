"""
Run Terraform CLI commands as pytest tests.
Requires `terraform` to be installed and on PATH.
No AWS credentials needed — uses -backend=false.
"""

import subprocess
import shutil
import os
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
INFRA_ROOT = os.path.join(REPO_ROOT, "devops", "infra")

terraform = shutil.which("terraform")


def tf(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [terraform, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


# ── Skip everything if terraform is not installed ─────────────────────────────

pytestmark = pytest.mark.skipif(
    terraform is None,
    reason="terraform binary not found — install Terraform >= 1.7 to run these tests",
)


# ── Format ────────────────────────────────────────────────────────────────────

def test_terraform_fmt_check():
    result = tf(["fmt", "-check", "-recursive", "devops/infra/"], cwd=REPO_ROOT)
    assert result.returncode == 0, (
        f"terraform fmt -check failed — run `terraform fmt -recursive devops/infra/` to fix:\n"
        f"{result.stdout}"
    )


# ── Validate environments ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def init_dev(tmp_path_factory):
    env_dir = os.path.join(INFRA_ROOT, "environments", "dev")
    result = tf(["init", "-backend=false", "-no-color"], cwd=env_dir)
    assert result.returncode == 0, f"terraform init failed for dev:\n{result.stderr}"
    return env_dir


@pytest.fixture(scope="module")
def init_prod(tmp_path_factory):
    env_dir = os.path.join(INFRA_ROOT, "environments", "prod")
    result = tf(["init", "-backend=false", "-no-color"], cwd=env_dir)
    assert result.returncode == 0, f"terraform init failed for prod:\n{result.stderr}"
    return env_dir


def test_dev_environment_validates(init_dev):
    result = tf(["validate", "-no-color"], cwd=init_dev)
    assert result.returncode == 0, (
        f"terraform validate failed for dev environment:\n{result.stderr}"
    )


def test_prod_environment_validates(init_prod):
    result = tf(["validate", "-no-color"], cwd=init_prod)
    assert result.returncode == 0, (
        f"terraform validate failed for prod environment:\n{result.stderr}"
    )


# ── Module unit tests (mock_provider — no AWS creds needed) ──────────────────

@pytest.fixture(scope="module")
def init_sg_module():
    module_dir = os.path.join(INFRA_ROOT, "modules", "security-groups")
    result = tf(["init", "-no-color"], cwd=module_dir)
    assert result.returncode == 0, f"terraform init failed for security-groups:\n{result.stderr}"
    return module_dir


@pytest.fixture(scope="module")
def init_vpc_module():
    module_dir = os.path.join(INFRA_ROOT, "modules", "vpc")
    result = tf(["init", "-no-color"], cwd=module_dir)
    assert result.returncode == 0, f"terraform init failed for vpc:\n{result.stderr}"
    return module_dir


def test_security_groups_module_tests_pass(init_sg_module):
    result = tf(["test", "-no-color"], cwd=init_sg_module)
    assert result.returncode == 0, (
        f"terraform test failed for security-groups module:\n{result.stdout}\n{result.stderr}"
    )


def test_vpc_module_tests_pass(init_vpc_module):
    result = tf(["test", "-no-color"], cwd=init_vpc_module)
    assert result.returncode == 0, (
        f"terraform test failed for vpc module:\n{result.stdout}\n{result.stderr}"
    )
