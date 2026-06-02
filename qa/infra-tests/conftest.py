import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
INFRA_ROOT = os.path.join(REPO_ROOT, "devops", "infra")


def read_env(env: str, filename: str = "main.tf") -> str:
    path = os.path.join(INFRA_ROOT, "environments", env, filename)
    with open(path) as f:
        return f.read()


def read_module(module: str, filename: str = "main.tf") -> str:
    path = os.path.join(INFRA_ROOT, "modules", module, filename)
    with open(path) as f:
        return f.read()


def has_setting(content: str, key: str, value: str) -> bool:
    """Return True when `key = value` appears (whitespace-tolerant)."""
    pattern = rf"{re.escape(key)}\s*=\s*{re.escape(value)}"
    return bool(re.search(pattern, content))
