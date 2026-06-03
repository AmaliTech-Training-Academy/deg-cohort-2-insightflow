#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# InsightFlow — zero-downtime deploy (build on EC2, no container registry)
#
# Called by GitHub Actions via SSM RunShellScript.
# The CI workflow uploads two files to the EC2 instance before running this:
#
#   /tmp/deploy.env   — environment config from devops/scripts/envs/<env>.env
#   /tmp/deploy.sh    — this script
#
# Required env vars (injected by CI into the SSM command):
#   COMMIT_SHA         full git SHA to deploy
#   GITHUB_REPO_URL    HTTPS clone URL  (e.g. https://github.com/org/repo.git)
#   GITHUB_TOKEN       Fine-grained PAT with contents:read
#
# Environment config (sourced from /tmp/deploy.env):
#   DEPLOY_ENV         dev | prod
#   APP_DIR            runtime dir   (e.g. /opt/insightflow)
#   REPO_DIR           source clone  (e.g. /opt/insightflow/repo)
#   COMPOSE_PROJECT    docker compose project name
#   AWS_REGION
#   CANARY_PORT        port for pre-flight canary (default 8081)
#   HEALTH_CHECK_PATH  (default /api-docs/)
#   HEALTH_CHECK_RETRIES
#   HEALTH_CHECK_INTERVAL
#   IMAGE_PRUNE_KEEP_DAYS
#   DEPLOY_TIMEOUT
#
# App secrets (already on disk from EC2 bootstrap):
#   /opt/insightflow/.env   — DJANGO_SECRET_KEY, DB_HOST, DB_PASSWORD, etc.
#                             The deploy script ONLY updates DEPLOY_TAG in this
#                             file; all other values are left untouched.
#
# Deploy flow:
#   1.  Source /tmp/deploy.env
#   2.  Validate required vars
#   3.  Record rollback point (current DEPLOY_TAG)
#   4.  git fetch + checkout COMMIT_SHA (first deploy: clone)
#   5.  Build images tagged insightflow-backend:sha-<short>
#   6.  Canary pre-flight  → new image on CANARY_PORT, health-check it
#   7.  Update DEPLOY_TAG in .env, docker compose up --no-deps backend + etl
#   8.  Post-deploy health check on port 8080
#   9.  Auto-rollback on failure
#  10.  Prune old images
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Source environment config ─────────────────────────────────────────────────
[[ -f /tmp/deploy.env ]] \
  || { echo "FATAL: /tmp/deploy.env not found — was it uploaded by CI?"; exit 1; }
# shellcheck source=/dev/null
source /tmp/deploy.env

# ── Validate required inputs ──────────────────────────────────────────────────
: "${COMMIT_SHA:?Must be set by CI}"
: "${GITHUB_REPO_URL:?Must be set by CI}"
: "${APP_DIR:?Must come from deploy.env}"
: "${REPO_DIR:?Must come from deploy.env}"
: "${DEPLOY_ENV:?Must come from deploy.env}"
# GITHUB_TOKEN is optional — only needed for private repos

# ── Derived constants ─────────────────────────────────────────────────────────
SHA_SHORT="${COMMIT_SHA:0:7}"
DEPLOY_TAG="sha-${SHA_SHORT}"
APP_ENV_FILE="${APP_DIR}/.env"
ROLLBACK_FILE="${APP_DIR}/.rollback"
PROJECT="${COMPOSE_PROJECT:-insightflow}"
COMPOSE="docker compose \
  -f ${REPO_DIR}/docker-compose.yml \
  --env-file ${APP_ENV_FILE} \
  --project-name ${PROJECT}"
LOG_TAG="deploy[${DEPLOY_ENV}/${SHA_SHORT}]"
CANARY_PORT="${CANARY_PORT:-8081}"
HC_PATH="${HEALTH_CHECK_PATH:-/api-docs/}"
HC_RETRIES="${HEALTH_CHECK_RETRIES:-24}"
HC_INTERVAL="${HEALTH_CHECK_INTERVAL:-5}"

log() { echo "$(date -u '+%H:%M:%S') [${LOG_TAG}] $*"; }
die() { log "FATAL: $*"; exit 1; }

# ── 0. Sanity ─────────────────────────────────────────────────────────────────
[[ -d "$APP_DIR" ]] \
  || die "APP_DIR=$APP_DIR not found — EC2 bootstrap must create it"
[[ -f "$APP_ENV_FILE" ]] \
  || die "$APP_ENV_FILE not found — EC2 bootstrap must write app secrets here"
mkdir -p "$REPO_DIR"

# ── 1. Record rollback point ──────────────────────────────────────────────────
PREV_TAG=$(grep -E '^DEPLOY_TAG=' "$APP_ENV_FILE" 2>/dev/null \
           | cut -d= -f2- || echo "local")
log "Rollback point: DEPLOY_TAG=${PREV_TAG}"
echo "$PREV_TAG" > "$ROLLBACK_FILE"

# ── 2. Update source code ─────────────────────────────────────────────────────
# For public repos no token is needed. For private repos set GITHUB_TOKEN.
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
  GIT_OPTS=(-c "credential.helper=!f() { echo username=x-access-token; echo password=${GITHUB_TOKEN}; }; f")
else
  GIT_OPTS=()
fi

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  log "First deploy — cloning ${GITHUB_REPO_URL} → ${REPO_DIR}"
  git "${GIT_OPTS[@]}" clone --filter=blob:none --no-checkout "$GITHUB_REPO_URL" "$REPO_DIR"
fi

cd "$REPO_DIR"
log "Fetching origin..."
git "${GIT_OPTS[@]}" fetch --quiet origin
git checkout --quiet --detach "$COMMIT_SHA"
log "Checked out ${COMMIT_SHA}"

# ── 3. Build new images ───────────────────────────────────────────────────────
log "Building backend, frontend and etl → insightflow-{backend,frontend,etl}:${DEPLOY_TAG}"
DEPLOY_TAG="$DEPLOY_TAG" $COMPOSE build \
  --parallel \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  backend frontend etl
log "Build complete"

# ── 4. Canary pre-flight ──────────────────────────────────────────────────────
log "Starting canary on port ${CANARY_PORT}..."
docker rm -f insightflow-canary 2>/dev/null || true

docker run -d \
  --name      insightflow-canary \
  --network   "${PROJECT}_default" \
  --env-file  "$APP_ENV_FILE" \
  -e          "DEPLOY_TAG=${DEPLOY_TAG}" \
  -p          "127.0.0.1:${CANARY_PORT}:8080" \
  "insightflow-backend:${DEPLOY_TAG}" \
  gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 60 \
           insightflow.wsgi:application

CANARY_OK=false
for i in $(seq 1 "$HC_RETRIES"); do
  HTTP=$(curl -sf -o /dev/null -w "%{http_code}" \
         "http://127.0.0.1:${CANARY_PORT}${HC_PATH}" 2>/dev/null || echo "000")
  log "  canary [$i/${HC_RETRIES}] HTTP ${HTTP}"
  if [[ "$HTTP" == "200" ]]; then CANARY_OK=true; break; fi
  sleep "$HC_INTERVAL"
done

docker rm -f insightflow-canary 2>/dev/null || true

if [[ "$CANARY_OK" != "true" ]]; then
  die "Canary failed — production traffic is unchanged, deploy aborted"
fi
log "Canary passed — proceeding with live rollout"

# ── 5. Update DEPLOY_TAG and rolling-replace ──────────────────────────────────
log "Updating DEPLOY_TAG → ${DEPLOY_TAG} in ${APP_ENV_FILE}"
TMP=$(mktemp)
grep -v '^DEPLOY_TAG=' "$APP_ENV_FILE" > "$TMP"
echo "DEPLOY_TAG=${DEPLOY_TAG}" >> "$TMP"
mv "$TMP" "$APP_ENV_FILE"

log "Rolling-replacing backend..."
$COMPOSE up -d --no-deps --remove-orphans backend

log "Rolling-replacing celery-worker..."
$COMPOSE up -d --no-deps --remove-orphans celery-worker

log "Rolling-replacing frontend..."
$COMPOSE up -d --no-deps --remove-orphans frontend

log "Rolling-replacing etl..."
$COMPOSE up -d --no-deps --remove-orphans etl

# ── 6. Post-deploy health check ───────────────────────────────────────────────
log "Post-deploy health check (port 8080)..."
LIVE_OK=false
for i in $(seq 1 30); do
  HTTP=$(curl -sf -o /dev/null -w "%{http_code}" \
         "http://127.0.0.1:8080${HC_PATH}" 2>/dev/null || echo "000")
  log "  live [$i/30] HTTP ${HTTP}"
  if [[ "$HTTP" == "200" ]]; then LIVE_OK=true; break; fi
  sleep "$HC_INTERVAL"
done

# ── 7. Auto-rollback ──────────────────────────────────────────────────────────
if [[ "$LIVE_OK" != "true" ]]; then
  log "Post-deploy health check FAILED — rolling back to ${PREV_TAG}"
  TMP=$(mktemp)
  grep -v '^DEPLOY_TAG=' "$APP_ENV_FILE" > "$TMP"
  echo "DEPLOY_TAG=${PREV_TAG}" >> "$TMP"
  mv "$TMP" "$APP_ENV_FILE"
  $COMPOSE up -d --no-deps --remove-orphans backend celery-worker frontend
  sleep 15
  RB_HTTP=$(curl -sf -o /dev/null -w "%{http_code}" \
            "http://127.0.0.1:8080${HC_PATH}" 2>/dev/null || echo "000")
  log "Rollback health: HTTP ${RB_HTTP}"
  die "Deploy failed; rolled back to ${PREV_TAG} (HTTP ${RB_HTTP})"
fi

# ── 8. Prune old images ───────────────────────────────────────────────────────
PRUNE_DAYS="${IMAGE_PRUNE_KEEP_DAYS:-3}"
log "Pruning images older than ${PRUNE_DAYS} days..."
docker image prune -f --filter "until=${PRUNE_DAYS}d" 2>/dev/null || true

$COMPOSE ps
log "Deploy complete! DEPLOY_TAG=${DEPLOY_TAG}"
