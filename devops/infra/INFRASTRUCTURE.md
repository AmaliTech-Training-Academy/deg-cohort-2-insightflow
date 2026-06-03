# InsightFlow — Infrastructure Reference

**Region:** `eu-west-1` (Singapore)
**IaC tool:** Terraform ≥ 1.6
**Environments:** `dev` · `prod`
**Last updated:** 2026-06-02

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Module Map](#2-module-map)
3. [Network Layer (VPC)](#3-network-layer-vpc)
4. [Security Groups](#4-security-groups)
5. [Compute — EC2](#5-compute--ec2)
6. [Databases — RDS PostgreSQL](#6-databases--rds-postgresql)
7. [Cache — ElastiCache Redis](#7-cache--elasticache-redis)
8. [Traffic Routing — ALB + WAF (Prod only)](#8-traffic-routing--alb--waf-prod-only)
9. [Storage — S3 & ECR](#9-storage--s3--ecr)
10. [Secrets Management](#10-secrets-management)
11. [CI/CD Pipelines](#11-cicd-pipelines)
12. [Environment Comparison](#12-environment-comparison)
13. [Cost Estimate](#13-cost-estimate)
14. [First-Time Setup Guide](#14-first-time-setup-guide)

---

## 1. Architecture Overview

```
                         INTERNET
         ┌────────────────────────────────────────┐
         │  Users      Store Mgrs   Orders API    │
         │  (HTTPS)    (CSV upload) (REST)        │
         └──────────────────┬─────────────────────┘
                            │ HTTPS :443
                      ┌─────▼──────┐
                      │  WAF v2    │  ← OWASP rules + rate limit
                      │  (prod)    │      (skipped in dev)
                      └─────┬──────┘
                            │
                      ┌─────▼──────┐
                      │    ALB     │  ← TLS termination, path routing
                      │  (prod)    │      (skipped in dev)
                      └─────┬──────┘
   ═══════════════ VPC ══════════════════════════════════
   ┌─── Public subnet ─────────────────────────────────┐
   │   ALB  ·  NAT Gateway                             │
   └──────────────────────┬────────────────────────────┘
   ┌─── Private subnet ───▼────────────────────────────┐
   │                                                    │
   │   ┌──────────────────────────────────────────┐    │
   │   │  EC2  (no public IP · SSM access only)   │    │
   │   │  ┌────────┐ ┌──────────┐ ┌───────────┐  │    │
   │   │  │Frontend│ │Django API│ │ETL runner │  │    │
   │   │  │React   │ │Gunicorn  │ │Pandas /   │  │    │
   │   │  │:3000   │ │:8080     │ │SQLAlchemy │  │    │
   │   │  └────────┘ └──────────┘ └───────────┘  │    │
   │   │         Docker Compose network            │    │
   │   └──────────────────────────────────────────┘    │
   │                                                    │
   │   ┌─────────────┐   ┌─────────────────────────┐  │
   │   │  RDS App DB │   │   RDS Warehouse DB       │  │
   │   │ PostgreSQL16│   │   PostgreSQL 16          │  │
   │   │ OLTP :5432  │   │   OLAP :5432             │  │
   │   └─────────────┘   └─────────────────────────┘  │
   │                                                    │
   │   ┌───────────────────────────────────────────┐   │
   │   │  ElastiCache Redis 7.1  ·  :6379          │   │
   │   │  Django cache (DB 0)  ·  ETL state (DB 1) │   │
   │   └───────────────────────────────────────────┘   │
   └────────────────────────────────────────────────────┘
   ═══════════════════════════════════════════════════════

   AWS Global Services
   ┌──────────┐ ┌───────────────┐ ┌────────┐ ┌─────────┐
   │    S3    │ │Secrets Manager│ │  ECR   │ │CloudWatch│
   │ (uploads)│ │ DB · Redis    │ │ images │ │  Logs   │
   └──────────┘ └───────────────┘ └────────┘ └─────────┘

   CI/CD
   ┌──────────────────────────────────────────────────┐
   │  GitHub Actions  →  OIDC  →  IAM role           │
   │  terraform apply  →  docker build  →  ECR push  │
   │  SSM send-command  →  docker compose up          │
   └──────────────────────────────────────────────────┘
```

---

## 2. Module Map

All infrastructure is composed from reusable modules under `devops/infra/modules/`.
Neither environment contains any inline `resource` blocks — every resource is managed by a module.

```
devops/infra/
├── modules/
│   ├── vpc/              VPC, subnets, IGW, NAT GW, route tables
│   ├── security-groups/  ALB · EC2 · RDS · Redis security groups
│   ├── ec2/              Instance, IAM role, Docker bootstrap user data
│   ├── rds/              App DB + Warehouse DB, Secrets Manager entries
│   ├── elasticache/      Redis cluster, parameter group, Secrets Manager entry
│   ├── alb/              ALB, target groups, listeners, WAF v2
│   ├── s3/               Uploads bucket, encryption, versioning
│   └── ecr/              backend + etl repositories, lifecycle policies
└── environments/
    ├── dev/              Calls all modules with dev-sized values
    └── prod/             Calls all modules with prod-sized values + ALB/WAF
```

---

## 3. Network Layer (VPC)

Each environment has its own fully isolated VPC.

| | Dev | Prod |
|---|---|---|
| VPC CIDR | `10.1.0.0/16` | `10.0.0.0/16` |
| Public subnet AZ-a | `10.1.1.0/24` | `10.0.1.0/24` |
| Public subnet AZ-b | `10.1.2.0/24` | `10.0.2.0/24` |
| Private subnet AZ-a | `10.1.10.0/24` | `10.0.10.0/24` |
| Private subnet AZ-b | `10.1.11.0/24` | `10.0.11.0/24` |

### Subnet roles

| Subnet | Resources placed here |
|---|---|
| Public (AZ-a, AZ-b) | ALB (prod), NAT Gateway (both envs) |
| Private (AZ-a) | EC2 instance |
| Private (AZ-a + AZ-b) | RDS subnet group, ElastiCache subnet group |

> **Why two private subnets?** AWS requires RDS and ElastiCache subnet groups to span at least two Availability Zones, even when running single-AZ instances.

### Routing

```
Public subnets   → Internet Gateway   (inbound + outbound)
Private subnets  → NAT Gateway        (outbound only — EC2 pulls from ECR,
                                       Secrets Manager, CloudWatch via NAT)
```

A single NAT Gateway in `public-a` handles outbound traffic for both private subnets. This is a cost optimisation — a second NAT GW in `public-b` would add ~$32/month with no benefit at single-AZ scale.

---

## 4. Security Groups

Traffic is controlled by four security groups that reference each other rather than using CIDR ranges wherever possible.

```
Internet
   │  :443 / :80
   ▼
[sg-alb] ──→ [sg-ec2] :3000 / :8080
                 │
                 ├──→ [sg-rds]   :5432
                 │
                 └──→ [sg-redis] :6379
```

| Security Group | Inbound | Outbound |
|---|---|---|
| `sg-alb` | 443, 80 from `0.0.0.0/0` | all (to EC2) |
| `sg-ec2` | 3000, 8080 from `sg-alb` only *(dev: no inbound at all)* | all (via NAT) |
| `sg-rds` | 5432 from `sg-ec2` only | all |
| `sg-redis` | 6379 from `sg-ec2` only | all |

> **Port 22 is permanently closed.** Shell access is via AWS SSM Session Manager only.

---

## 5. Compute — EC2

One EC2 instance per environment runs the entire application stack as Docker Compose services.

### Instance configuration

| | Dev | Prod |
|---|---|---|
| Instance type | `t3.small` (2 vCPU, 2 GB RAM) | `t3.medium` (2 vCPU, 4 GB RAM) |
| Root volume | 20 GB gp3, encrypted | 30 GB gp3, encrypted |
| Public IP | None | None |
| AMI | Amazon Linux 2023 (latest) | Amazon Linux 2023 (latest) |
| Metadata | IMDSv2 required | IMDSv2 required |
| CloudWatch log retention | 7 days | 30 days |

### Application containers (Docker Compose)

| Container | Port | Description |
|---|---|---|
| `frontend` | 3000 | React app served by Nginx |
| `backend` | 8080 | Django REST API — Gunicorn 4 workers |
| `etl` | — | Ephemeral ETL runner (Pandas · SQLAlchemy), `restart: no` |
| `nginx` | — | Internal reverse proxy |

### IAM role (least privilege)

The EC2 instance profile grants only what the application needs:

| Permission | Scope |
|---|---|
| `AmazonSSMManagedInstanceCore` | SSM shell + deploy access |
| `AmazonEC2ContainerRegistryReadOnly` | Pull images from ECR |
| `secretsmanager:GetSecretValue` | Secrets under `insightflow-{env}/*` only |
| `s3:GetObject / PutObject / DeleteObject / ListBucket` | The env uploads bucket only |
| `logs:PutLogEvents` | Log groups under `/insightflow/{env}/*` only |

### Bootstrap (user data)

On first boot, the EC2 instance automatically:
1. Installs Docker and the Docker Compose v2 plugin
2. Authenticates with ECR
3. Sets up an ECR re-authentication cron job (every 11 hours)
4. Creates `/opt/insightflow/` as the app working directory

---

## 6. Databases — RDS PostgreSQL

Two separate PostgreSQL 16 RDS instances per environment, both in the private subnet with no public access.

### App DB (`insightflow_app`) — OLTP

Used by the Django API for users, authentication, ingestion jobs, and pipeline state.

- **Connection:** via `DB_HOST` env var (hostname from Secrets Manager)
- **Port:** 5432
- **Access:** `sg-ec2` only

### Warehouse DB (`insightflow_warehouse`) — OLAP

ETL pipeline writes transformed star-schema tables here. Streamlit connects directly to this DB for reporting.

- **Connection:** via `WAREHOUSE_DB_HOST` env var (hostname from Secrets Manager)
- **Port:** 5432
- **Access:** `sg-ec2` only

### Configuration comparison

| Setting | Dev | Prod |
|---|---|---|
| Instance class | `db.t3.micro` | `db.t3.small` |
| Storage | 20 GB gp3, encrypted | 20 GB gp3, encrypted |
| Multi-AZ standby | No | No *(enable when budget allows)* |
| Deletion protection | Off | **On** |
| Final snapshot | Skipped (fast teardown) | **Taken** |
| Backup retention | 1 day | 7 days |
| Performance Insights | Off | On (free tier) |

### Secrets Manager layout

```
insightflow-dev/db/app        → { host, port, dbname, username, password }
insightflow-dev/db/warehouse  → { host, port, dbname, username, password }
insightflow-prod/db/app       → { host, port, dbname, username, password }
insightflow-prod/db/warehouse → { host, port, dbname, username, password }
```

---

## 7. Cache — ElastiCache Redis

One single-node Redis 7.1 cluster per environment, in the private subnet.

### Usage by service

| Service | Redis DB | Purpose |
|---|---|---|
| Django API (`backend`) | DB 0 | Django cache framework, session storage |
| ETL runner (`etl`) | DB 1 | Job state tracking, intermediate results |

### Configuration comparison

| Setting | Dev | Prod |
|---|---|---|
| Node type | `cache.t3.micro` | `cache.t3.small` |
| Engine | Redis 7.1 | Redis 7.1 |
| At-rest encryption | On | On |
| In-transit TLS mode | `preferred` | `required` |
| Snapshots | Off | 1 day |
| Apply changes | Immediately | Maintenance window |
| Eviction policy | `allkeys-lru` | `allkeys-lru` |

### Connection URL format

```
Local dev (Docker):   redis://redis:6379/{db}
AWS dev/prod:         rediss://<elasticache-endpoint>:6379/{db}
```

> The `rediss://` scheme (double-s) enables TLS. The endpoint and full URL are stored in Secrets Manager at `insightflow-{env}/redis/endpoint`.

---

## 8. Traffic Routing — ALB + WAF (Prod only)

In development, there is no load balancer. Developers access the EC2 via SSM port-forwarding and test locally.

In production, all traffic passes through two layers before reaching EC2:

### WAF v2

| Rule | Action |
|---|---|
| AWS Managed Rules — Common Rule Set | Block (OWASP Top 10, SQLi, XSS, bad bots) |
| Rate limit — 2,000 req / IP / 5 min | Block |

### Application Load Balancer

```
:80  HTTP  → redirect 301 → HTTPS

:443 HTTPS → path-based routing:
  /api/*         → Django API target group  (:8080)
  /api-docs/*    → Django API target group  (:8080)
  /swagger-ui/*  → Django API target group  (:8080)
  /admin/*       → Django API target group  (:8080)
  /*             → Frontend target group    (:3000)
```

- **TLS policy:** `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.2 minimum, TLS 1.3 preferred)
- **Certificate:** ACM — auto-renewed, same region as ALB
- **Health checks:** `/` on port 3000 (frontend), `/api-docs/` on port 8080 (API)

---

## 9. Storage — S3 & ECR

### S3 — Uploads bucket

One bucket per environment for CSV uploads and exported reports.

| Setting | Dev | Prod |
|---|---|---|
| Public access | Fully blocked | Fully blocked |
| Versioning | Off | On |
| Encryption | SSE-S3 (AES-256) | SSE-S3 (AES-256) |
| Naming | `insightflow-dev-uploads-{account_id}` | `insightflow-prod-uploads-{account_id}` |

### ECR — Container image registry

Two repositories shared across both environments:

| Repository | Contents |
|---|---|
| `insightflow/backend` | Django API image |
| `insightflow/etl` | ETL pipeline image |

| Setting | Dev | Prod |
|---|---|---|
| Scan on push | Yes | Yes |
| Images retained | 5 | 10 |
| Tag format | `dev-<sha>`, `dev-latest` | `<sha>`, `latest` |

---

## 10. Secrets Management

All sensitive values are stored in **AWS Secrets Manager**. No secret is ever written to a file, environment variable at the Terraform level, or the repository.

### Secret layout

```
insightflow-{env}/
├── db/
│   ├── app          { host, port, dbname, username, password }
│   └── warehouse    { host, port, dbname, username, password }
└── redis/
    └── endpoint     { host, port, url }
```

### How secrets reach the application

1. EC2 boots → Docker Compose starts
2. Each container reads its secret from Secrets Manager at startup using the AWS SDK or a startup script
3. The EC2 IAM role allows `secretsmanager:GetSecretValue` on `insightflow-{env}/*` — nothing outside that prefix is accessible

### GitHub Actions secrets (CI/CD)

These are stored in GitHub Secrets, not in the repo:

| Secret | Used by |
|---|---|
| `AWS_DEPLOY_ROLE_DEV` | Dev deploy workflow (OIDC role ARN) |
| `AWS_DEPLOY_ROLE_PROD` | Prod deploy workflow (OIDC role ARN) |
| `DEV_APP_DB_PASSWORD` | Terraform — sets RDS master password |
| `DEV_WAREHOUSE_DB_PASSWORD` | Terraform — sets RDS master password |
| `PROD_APP_DB_PASSWORD` | Terraform — sets RDS master password |
| `PROD_WAREHOUSE_DB_PASSWORD` | Terraform — sets RDS master password |
| `PROD_ACM_CERT_ARN` | Terraform — attaches cert to ALB HTTPS listener |

---

## 11. CI/CD Pipelines

### ci.yml — runs on every PR and push to `main` / `dev`

```
push / PR
    │
    ├─ changes (path detection)
    │
    ├─ lint          → pre-commit hooks · mypy type check
    ├─ security      → gitleaks (secret scan) · pip-audit (CVE check)
    ├─ backend       → Django system check · migrations · pytest + coverage
    ├─ data-eng      → syntax check · ETL tests
    ├─ api-tests     → integration tests against live Django + Postgres
    ├─ docker        → docker build · Trivy image scan (CRITICAL CVEs)
    └─ infrastructure→ checkov IaC scan · terraform fmt · terraform validate
            │
            └─ ci-passed (required status check for branch protection)
```

### deploy-dev.yml — triggers on push to `dev`

```
push to dev
    │
    ├─ infrastructure  terraform init → validate → plan → apply
    │                  (reads DEV_* secrets as TF_VAR_)
    │
    ├─ build           docker build backend + etl
    │                  → push to ECR with dev-<sha> and dev-latest tags
    │
    └─ deploy          SSM send-command to EC2:
                       ecr-login → docker compose pull → docker compose up -d
```

### deploy-prod.yml — triggers on push to `main`

```
push to main
    │
    ├─ plan            terraform init → validate → plan → apply
    │                  (reads PROD_* secrets as TF_VAR_)
    │
    ├─ build           docker build backend + etl
    │                  → push to ECR with <sha> and latest tags
    │
    └─ deploy ← ⚠️ requires manual approval (GitHub Environment: production)
                       SSM send-command to EC2:
                       ecr-login → docker compose pull → docker compose up -d
                       → smoke test: curl ALB /api-docs/ → expect HTTP 200
```

> **Authentication:** GitHub Actions uses **OIDC federation** to assume an IAM role directly. No long-lived AWS access keys are stored in GitHub Secrets.

---

## 12. Environment Comparison

| Aspect | Dev | Prod |
|---|---|---|
| VPC CIDR | `10.1.0.0/16` | `10.0.0.0/16` |
| EC2 type | `t3.small` | `t3.medium` |
| RDS class | `db.t3.micro` | `db.t3.small` |
| Redis type | `cache.t3.micro` | `cache.t3.small` |
| ALB | No | Yes |
| WAF | No | Yes |
| RDS deletion protection | Off | On |
| RDS Multi-AZ | No | No |
| S3 versioning | Off | On |
| ECR images kept | 5 | 10 |
| Redis TLS mode | preferred | required |
| Redis snapshots | Off | 1 day |
| Log retention | 7 days | 30 days |
| Deploy approval | Automatic | Manual gate |
| Shell access | SSM only | SSM only |

---

## 13. Cost Estimate

Approximate monthly costs in `eu-west-1` at on-demand pricing.

| Service | Dev | Prod |
|---|---|---|
| EC2 (`t3.small` / `t3.medium`) | ~$17 | ~$33 |
| RDS App DB | ~$14 | ~$28 |
| RDS Warehouse DB | ~$14 | ~$28 |
| ElastiCache Redis | ~$12 | ~$24 |
| NAT Gateway (fixed + data) | ~$32 | ~$32 |
| ALB | — | ~$16 |
| WAF v2 | — | ~$5 |
| S3 + ECR + Secrets Manager | ~$1 | ~$2 |
| CloudWatch Logs | ~$1 | ~$2 |
| **Estimated total** | **~$91/mo** | **~$170/mo** |

> Costs vary with traffic and data transfer. The NAT Gateway fixed fee (~$32) dominates the dev bill — this can be eliminated if dev services are moved to public subnets with restrictive security groups, at the cost of reduced prod-parity.

---

## 14. First-Time Setup Guide

### Prerequisites

- AWS CLI configured with admin credentials
- Terraform ≥ 1.6 installed
- An ACM certificate requested in `eu-west-1` for your domain (prod only)

### Step 1 — Bootstrap Terraform remote state

Create the S3 bucket and DynamoDB lock table once (manually or via a bootstrap script):

```bash
aws s3api create-bucket \
  --bucket insightflow-tfstate \
  --region eu-west-1 \
  --create-bucket-configuration LocationConstraint=eu-west-1

aws s3api put-bucket-versioning \
  --bucket insightflow-tfstate \
  --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name insightflow-tfstate-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

Then uncomment the `backend "s3"` block in `environments/dev/main.tf` and `environments/prod/main.tf`.

### Step 2 — Create GitHub OIDC IAM roles

Create two IAM roles (`insightflow-github-deploy-dev` and `insightflow-github-deploy-prod`) with an OIDC trust policy for `token.actions.githubusercontent.com` scoped to your repo and the correct branch. Attach the minimum permissions needed for Terraform to manage the resources in each environment.

### Step 3 — Set GitHub Secrets

In your GitHub repository → Settings → Secrets and variables → Actions:

```
AWS_DEPLOY_ROLE_DEV        arn:aws:iam::<account>:role/insightflow-github-deploy-dev
AWS_DEPLOY_ROLE_PROD       arn:aws:iam::<account>:role/insightflow-github-deploy-prod
DEV_APP_DB_PASSWORD        <strong-password>
DEV_WAREHOUSE_DB_PASSWORD  <strong-password>
PROD_APP_DB_PASSWORD       <strong-password>
PROD_WAREHOUSE_DB_PASSWORD <strong-password>
PROD_ACM_CERT_ARN          arn:aws:acm:eu-west-1:<account>:certificate/<id>
```

### Step 4 — Deploy dev

```bash
cd devops/infra/environments/dev
terraform init
terraform plan   # review
terraform apply
```

### Step 5 — Deploy prod

```bash
cd devops/infra/environments/prod
terraform init
terraform plan   # review
terraform apply
```

### Step 6 — Connect to EC2 (shell access)

```bash
# Get instance ID from Terraform output
terraform output ec2_instance_id

# Open an interactive shell — no SSH key needed
aws ssm start-session --target <instance-id> --region eu-west-1
```

### Step 7 — Set up GitHub Environment gate (prod)

In GitHub → Settings → Environments → create `production` → add required reviewers. The prod deploy workflow will pause at the `deploy` job until a reviewer approves.
