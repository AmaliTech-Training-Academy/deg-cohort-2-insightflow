#!/bin/bash
# Starts all InsightFlow dev tunnels via SSM.
# Keep this running in a terminal, then use the real RDS/Redis hostnames normally.
# Requires: AWS CLI + SSM plugin installed, AWS credentials configured.

INSTANCE="i-0905ce991370e506b"
REGION="eu-west-1"

APP_DB="insightflow-dev-app-db.cf6io6y406u0.eu-west-1.rds.amazonaws.com"
WH_DB="insightflow-dev-warehouse-db.cf6io6y406u0.eu-west-1.rds.amazonaws.com"
REDIS="master.insightflow-dev-redis.ony2gf.euw1.cache.amazonaws.com"

echo "Opening InsightFlow dev tunnels..."
echo "  App DB      -> localhost:5432"
echo "  Warehouse   -> localhost:5433"
echo "  Redis       -> localhost:6379"
echo ""
echo "Keep this terminal open. Ctrl+C to close all tunnels."
echo ""

# Open all three tunnels in background
aws ssm start-session \
  --target "$INSTANCE" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$APP_DB\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}" \
  --region "$REGION" &

aws ssm start-session \
  --target "$INSTANCE" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$WH_DB\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5433\"]}" \
  --region "$REGION" &

aws ssm start-session \
  --target "$INSTANCE" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$REDIS\"],\"portNumber\":[\"6379\"],\"localPortNumber\":[\"6379\"]}" \
  --region "$REGION" &

# Wait for all tunnels — Ctrl+C kills them all cleanly
wait