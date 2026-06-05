import os
import urllib.request

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(
    ","
)

# On EC2, the ALB health check sends requests with Host: <private-ip>:<port>.
# Fetch the instance's private IP from the metadata service and add it so
# Django doesn't reject those requests with DisallowedHost.
try:
    _ec2_private_ip = (
        urllib.request.urlopen(  # nosec B310 — hardcoded EC2 metadata endpoint, not user input
            "http://169.254.169.254/latest/meta-data/local-ipv4", timeout=0.5
        )
        .read()
        .decode()
        .strip()
    )
    if _ec2_private_ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_ec2_private_ip)
except Exception:  # nosec B110 — metadata unavailable outside EC2; silent failure is correct
    pass

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
