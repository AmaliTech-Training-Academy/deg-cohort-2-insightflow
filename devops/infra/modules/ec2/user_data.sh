#!/bin/bash
set -euo pipefail

# Install system packages
dnf install -y docker socat git
systemctl enable --now docker

# Docker Compose v2 + buildx plugins
mkdir -p /usr/local/lib/docker/cli-plugins

COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest \
  | grep '"tag_name"' | cut -d'"' -f4)
curl -SL "https://github.com/docker/compose/releases/download/$${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# buildx — Compose v5 requires 0.17.0+; pin latest to avoid stale OS package
# shellcheck disable=SC2034  # $${BUILDX_VERSION} is Terraform-escaped ${BUILDX_VERSION}
BUILDX_VERSION=$(curl -s https://api.github.com/repos/docker/buildx/releases/latest \
  | grep '"tag_name"' | cut -d'"' -f4)
curl -SL "https://github.com/docker/buildx/releases/download/$${BUILDX_VERSION}/buildx-$${BUILDX_VERSION}.linux-amd64" \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# Allow ec2-user to run Docker without sudo
usermod -aG docker ec2-user

# App working directory
mkdir -p /opt/insightflow
chown ec2-user:ec2-user /opt/insightflow

# Fetch the full app .env from Secrets Manager — written by Terraform/ops when
# secrets change; the deploy script expects it at /opt/insightflow/.env.
aws secretsmanager get-secret-value \
  --region "${region}" \
  --secret-id "${name}/app/env" \
  --query SecretString \
  --output text > /opt/insightflow/.env
chmod 600 /opt/insightflow/.env
chown ec2-user:ec2-user /opt/insightflow/.env

# Authenticate Docker with ECR on boot (refreshed by cron every 11h)
cat > /usr/local/bin/ecr-login.sh <<'EOF'
#!/bin/bash
REGION="${region}"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin \
    "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
EOF
chmod +x /usr/local/bin/ecr-login.sh
/usr/local/bin/ecr-login.sh || true

echo "0 */11 * * * root /usr/local/bin/ecr-login.sh" > /etc/cron.d/ecr-login

# Log marker — visible in EC2 System Log
echo "InsightFlow (${name}) bootstrap complete"
