#!/usr/bin/env bash
# Poll an SSM RunShellScript command until it finishes, then print its output.
# Usage: ssm-wait.sh <command-id> <instance-id> [timeout-seconds]
set -euo pipefail

CMD_ID="$1"
INSTANCE_ID="$2"
TIMEOUT="${3:-300}"
INTERVAL=10
MAX=$(( TIMEOUT / INTERVAL ))

for i in $(seq 1 "$MAX"); do
  STATUS=$(aws ssm get-command-invocation \
    --command-id  "$CMD_ID" \
    --instance-id "$INSTANCE_ID" \
    --query "Status" --output text 2>/dev/null || echo "Pending")

  echo "[$i/$MAX] SSM status: $STATUS"

  case "$STATUS" in
    Success)
      aws ssm get-command-invocation \
        --command-id  "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardOutputContent" --output text || true
      exit 0
      ;;
    Failed|Cancelled|TimedOut)
      echo "=== STDOUT ===" >&2
      aws ssm get-command-invocation \
        --command-id  "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardOutputContent" --output text >&2 || true
      echo "=== STDERR ===" >&2
      aws ssm get-command-invocation \
        --command-id  "$CMD_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardErrorContent" --output text >&2 || true
      exit 1
      ;;
  esac

  sleep "$INTERVAL"
done

echo "ERROR: SSM command timed out after ${TIMEOUT}s" >&2
exit 1
