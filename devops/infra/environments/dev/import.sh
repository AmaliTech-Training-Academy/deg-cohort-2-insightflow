#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Re-import existing dev infrastructure into Terraform state.
# Run from: devops/infra/environments/dev/
#
# Steps:
#   1. Fill in every value in the "FILL IN FROM AWS CONSOLE" section below
#   2. chmod +x import.sh && ./import.sh
#   3. terraform plan   (should show no changes or only minor diffs)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ═════════════════════════════════════════════════════
#  FILL IN FROM AWS CONSOLE
# ═════════════════════════════════════════════════════

REGION="eu-west-1"
NAME="insightflow-dev"
ACCOUNT_ID=""               # AWS account ID (12 digits)

# EC2 → VPC
VPC_ID=""                   # vpc-xxxxxxxxxxxxxxxxx
IGW_ID=""                   # igw-xxxxxxxxxxxxxxxxx
SUBNET_PUB_A=""             # subnet-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-public-a)
SUBNET_PUB_B=""             # subnet-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-public-b)
SUBNET_PRIV_A=""            # subnet-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-private-a)
SUBNET_PRIV_B=""            # subnet-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-private-b)
EIP_ALLOC_ID=""             # eipalloc-xxxxxxxxxxxxxxxxx (Name: insightflow-dev-nat-eip)
NAT_GW_ID=""                # nat-xxxxxxxxxxxxxxxxx
RT_PUBLIC=""                # rtb-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-public-rt)
RT_PRIVATE=""               # rtb-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-private-rt)
DEFAULT_SG_ID=""            # sg-xxxxxxxxxxxxxxxxx   (default SG of the VPC)
FLOW_LOG_ID=""              # fl-xxxxxxxxxxxxxxxxx   (EC2 → VPC → Flow logs)

# EC2 → Security Groups
SG_ALB=""                   # sg-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-sg-alb)
SG_EC2=""                   # sg-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-sg-ec2)
SG_RDS=""                   # sg-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-sg-rds)
SG_REDIS=""                 # sg-xxxxxxxxxxxxxxxxx  (Name: insightflow-dev-sg-redis)

# EC2 → Instances
INSTANCE_ID=""              # i-xxxxxxxxxxxxxxxxx

# S3 bucket name (Buckets → insightflow-dev-uploads-<account-id>)
S3_BUCKET="${NAME}-uploads-${ACCOUNT_ID}"

# EC2 → Load Balancers
ALB_ARN=""                  # arn:aws:elasticloadbalancing:...
TG_FRONTEND_ARN=""          # arn:aws:elasticloadbalancing:...  (Name: insightflow-dev-tg-frontend)
TG_API_ARN=""               # arn:aws:elasticloadbalancing:...  (Name: insightflow-dev-tg-api)
LISTENER_HTTP_ARN=""        # arn:aws:elasticloadbalancing:...  (port 80 listener)

# RDS → Databases (identifiers, not ARNs)
# (RDS → Databases → DB identifier column)
# App DB identifier:       insightflow-dev-app-db
# Warehouse DB identifier: insightflow-dev-warehouse-db

# Secrets Manager ARNs (Secrets Manager → Secrets → ARN column)
SECRET_APP_DB_ARN=""        # arn:aws:secretsmanager:...:secret:insightflow-dev/db/app-...
SECRET_APP_DB_VER=""        # version ID of the AWSCURRENT version
SECRET_WAREHOUSE_ARN=""     # arn:aws:secretsmanager:...:secret:insightflow-dev/db/warehouse-...
SECRET_WAREHOUSE_VER=""     # version ID of the AWSCURRENT version
SECRET_REDIS_ARN=""         # arn:aws:secretsmanager:...:secret:insightflow-dev/redis/endpoint-...
SECRET_REDIS_VER=""         # version ID of the AWSCURRENT version

# ═════════════════════════════════════════════════════
#  END OF MANUAL SECTION — do not edit below this line
# ═════════════════════════════════════════════════════

tf_import() {
  local addr="$1" id="$2"
  if [[ -z "$id" ]]; then
    echo "   SKIP (empty): $addr"
    return
  fi
  echo "   importing $addr"
  terraform import "$addr" "$id" 2>&1 | tail -2 || echo "   WARN: import failed for $addr"
}

echo "Starting import for environment: $NAME ($REGION)"
echo ""

echo "── Key pair"
tf_import "aws_key_pair.dev" "${NAME}-key"

echo "── VPC"
tf_import "module.vpc.aws_vpc.this" "$VPC_ID"
tf_import "module.vpc.aws_internet_gateway.this" "$IGW_ID"

echo "── Subnets"
tf_import "module.vpc.aws_subnet.public_a"  "$SUBNET_PUB_A"
tf_import "module.vpc.aws_subnet.public_b"  "$SUBNET_PUB_B"
tf_import "module.vpc.aws_subnet.private_a" "$SUBNET_PRIV_A"
tf_import "module.vpc.aws_subnet.private_b" "$SUBNET_PRIV_B"

echo "── NAT gateway + EIP"
tf_import "module.vpc.aws_eip.nat"          "$EIP_ALLOC_ID"
tf_import "module.vpc.aws_nat_gateway.this" "$NAT_GW_ID"

echo "── Route tables"
tf_import "module.vpc.aws_route_table.public"  "$RT_PUBLIC"
tf_import "module.vpc.aws_route_table.private" "$RT_PRIVATE"

echo "── Route table associations"
tf_import "module.vpc.aws_route_table_association.public_a"  "${SUBNET_PUB_A}/${RT_PUBLIC}"
tf_import "module.vpc.aws_route_table_association.public_b"  "${SUBNET_PUB_B}/${RT_PUBLIC}"
tf_import "module.vpc.aws_route_table_association.private_a" "${SUBNET_PRIV_A}/${RT_PRIVATE}"
tf_import "module.vpc.aws_route_table_association.private_b" "${SUBNET_PRIV_B}/${RT_PRIVATE}"

echo "── Default security group + flow logs"
tf_import "module.vpc.aws_default_security_group.this"    "$DEFAULT_SG_ID"
tf_import "module.vpc.aws_cloudwatch_log_group.flow_logs" "/aws/vpc/flowlogs/${NAME}"
tf_import "module.vpc.aws_iam_role.flow_logs"             "${NAME}-vpc-flow-logs"
tf_import "module.vpc.aws_iam_role_policy.flow_logs"      "${NAME}-vpc-flow-logs:${NAME}-vpc-flow-logs"
tf_import "module.vpc.aws_flow_log.this"                  "$FLOW_LOG_ID"

echo "── Security groups"
tf_import "module.security_groups.aws_security_group.alb"   "$SG_ALB"
tf_import "module.security_groups.aws_security_group.ec2"   "$SG_EC2"
tf_import "module.security_groups.aws_security_group.rds"   "$SG_RDS"
tf_import "module.security_groups.aws_security_group.redis" "$SG_REDIS"

echo "── S3"
tf_import "module.s3.aws_s3_bucket.this"                                      "$S3_BUCKET"
tf_import "module.s3.aws_s3_bucket_public_access_block.this"                  "$S3_BUCKET"
tf_import "module.s3.aws_s3_bucket_server_side_encryption_configuration.this" "$S3_BUCKET"
tf_import "module.s3.aws_s3_bucket_versioning.this"                           "$S3_BUCKET"

echo "── EC2 IAM role + instance profile"
tf_import "module.ec2.aws_iam_role.ec2"                        "${NAME}-ec2-role"
tf_import "module.ec2.aws_iam_role_policy_attachment.ssm"      "${NAME}-ec2-role/arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
tf_import "module.ec2.aws_iam_role_policy_attachment.ecr_read" "${NAME}-ec2-role/arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
tf_import "module.ec2.aws_iam_role_policy.secrets_and_logs"    "${NAME}-ec2-role:${NAME}-ec2-secrets-logs"
tf_import "module.ec2.aws_iam_instance_profile.ec2"            "${NAME}-ec2-profile"

echo "── EC2 instance + log group"
tf_import "module.ec2.aws_instance.this"           "$INSTANCE_ID"
tf_import "module.ec2.aws_cloudwatch_log_group.app" "/insightflow/${NAME}/app"

echo "── RDS"
tf_import "module.rds.aws_db_subnet_group.this"        "${NAME}-rds-subnet-group"
tf_import "module.rds.aws_db_parameter_group.postgres16" "${NAME}-pg16"
tf_import "module.rds.aws_db_instance.app"             "${NAME}-app-db"
tf_import "module.rds.aws_db_instance.warehouse"       "${NAME}-warehouse-db"
tf_import "module.rds.aws_secretsmanager_secret.app_db"             "$SECRET_APP_DB_ARN"
tf_import "module.rds.aws_secretsmanager_secret_version.app_db"     "${SECRET_APP_DB_ARN}|${SECRET_APP_DB_VER}"
tf_import "module.rds.aws_secretsmanager_secret.warehouse_db"         "$SECRET_WAREHOUSE_ARN"
tf_import "module.rds.aws_secretsmanager_secret_version.warehouse_db" "${SECRET_WAREHOUSE_ARN}|${SECRET_WAREHOUSE_VER}"

echo "── ElastiCache Redis"
tf_import "module.redis.aws_elasticache_subnet_group.this"      "${NAME}-redis-subnet-group"
tf_import "module.redis.aws_elasticache_parameter_group.this"   "${NAME}-redis7"
tf_import "module.redis.aws_elasticache_replication_group.this" "${NAME}-redis"
tf_import "module.redis.aws_secretsmanager_secret.redis"         "$SECRET_REDIS_ARN"
tf_import "module.redis.aws_secretsmanager_secret_version.redis" "${SECRET_REDIS_ARN}|${SECRET_REDIS_VER}"

echo "── ALB + target groups + listener"
tf_import "module.alb.aws_lb.this"                          "$ALB_ARN"
tf_import "module.alb.aws_lb_target_group.frontend"         "$TG_FRONTEND_ARN"
tf_import "module.alb.aws_lb_target_group.api"              "$TG_API_ARN"
tf_import "module.alb.aws_lb_target_group_attachment.frontend" "${TG_FRONTEND_ARN}/${INSTANCE_ID}/80"
tf_import "module.alb.aws_lb_target_group_attachment.api"      "${TG_API_ARN}/${INSTANCE_ID}/8080"
tf_import "module.alb.aws_lb_listener.http"                 "$LISTENER_HTTP_ARN"

echo ""
echo "═══════════════════════════════════════════════════"
echo " Import complete."
echo " Next: terraform plan  (review any diffs)"
echo "═══════════════════════════════════════════════════"
