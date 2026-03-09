# Offering4AI Cloud Migration Plan

This document is the handoff plan for moving the current MVP from local Docker and the cheapest single-VM GCP deployment toward a more production-ready Google Cloud setup.

## Current state

Today the project supports:
- local Docker Compose development
- cheapest GCP deployment on a single Compute Engine VM
- optional Cloud Run deployment scripts for frontend, API, and worker

Current service model:
- `frontend` served by nginx
- `api` served by FastAPI
- `worker` served by RQ + Redis
- `postgres` as the primary relational store
- `redis` as the queue backend

## Migration goals

Move from the low-cost MVP footprint to a cleaner managed footprint while preserving:
- public AI-readable endpoints
- simple deployment flow via Codex CLI
- cheap operation at low traffic
- ability to grow without rewriting the app

## Recommended migration sequence

### Phase 0 — keep the current cheapest deployment usable

Use the single VM path while traffic is low and product copy, schema, and evaluation behavior are still changing.

Why:
- lowest monthly cost
- easiest debugging
- fastest iteration speed
- minimal infra sprawl

Keep using:
- `deploy/gcp/deploy-vm.sh`
- `deploy/gcp/docker-compose.vm.yml`
- `deploy/gcp/Caddyfile`

### Phase 1 — harden production basics on the VM

Before moving to managed services, complete these items:
- move production secrets out of plain env files and into Secret Manager or an encrypted secret workflow
- add scheduled backups for Postgres
- add VM snapshot policy
- add uptime checks for `/health` and the homepage
- add central log export or at least log retention strategy
- replace startup `create_all()` schema management with versioned migrations

Success criteria:
- restarts are predictable
- data recovery is defined
- production config is reproducible

### Phase 2 — split stateless services from stateful services

First managed move:
- move `postgres` from the VM to Cloud SQL for PostgreSQL
- move `redis` from the VM to Memorystore or, if cost matters more than purity, keep Redis on the VM temporarily

Why this is the best first migration:
- stateful services are the hardest to operate safely on a tiny VM
- frontend, API, and worker already containerize cleanly
- app code already uses env-based connection strings

Required changes:
- create Cloud SQL instance and database
- create DB user and strong password
- update `DATABASE_URL`
- create private or controlled network path from compute runtime to Cloud SQL
- create Redis instance if Memorystore is used and update `REDIS_URL`

Success criteria:
- app still runs from the VM
- state survives VM replacement
- backups and recovery improve materially

### Phase 3 — move stateless services to Cloud Run

Once the database and queue are stable outside the VM, move:
- `frontend` -> Cloud Run
- `api` -> Cloud Run
- `worker` -> Cloud Run with minimum instance `1`

Why now:
- stateless services become easier to scale and redeploy
- custom domain mapping becomes simpler
- VM can be retired or reduced to only legacy roles

Required infra:
- Artifact Registry
- Cloud Run services
- optional Serverless VPC Access connector
- domain mapping or HTTPS load balancer
- Secret Manager for secrets injection

Required app settings:
- `PUBLIC_API_BASE_URL`
- `PUBLIC_SITE_URL`
- `CORS_ALLOWED_ORIGINS`
- runtime frontend env vars for API and site URL

Success criteria:
- frontend and API run without the VM
- worker processes queue reliably
- public AI endpoints stay stable on the production domain

### Phase 4 — codify infrastructure

Once the target architecture is stable, add Terraform for:
- Artifact Registry
- service accounts and IAM
- firewall rules
- VM path resources
- Cloud Run path resources
- Cloud SQL
- Memorystore
- Secret Manager
- optional DNS resources

Why last:
- avoids freezing the wrong architecture too early
- keeps the first Terraform pass aligned with the deployment you actually want

## Two target end states

## Option A — lowest-cost steady state

Stay on one Compute Engine VM and harden operations.

Best when:
- traffic is still low
- budget is the main constraint
- you want one machine you can reason about easily

Tradeoffs:
- more ops burden
- stateful services remain your responsibility
- scaling is vertical rather than cleanly horizontal

## Option B — cleaner managed state

Move to:
- Cloud Run for `frontend`, `api`, and `worker`
- Cloud SQL for Postgres
- Memorystore for Redis
- Secret Manager for secrets

Best when:
- traffic is rising
- uptime expectations increase
- you want cleaner deployment boundaries

Tradeoffs:
- higher monthly baseline cost
- more GCP moving parts
- networking setup becomes more involved

## Open topics to resolve tomorrow

### Architecture
- Should the worker stay on Cloud Run or move to a VM/GKE if queue load grows?
- Is Redis still the right queue once durable retries matter more?
- Do we want a dedicated API subdomain such as `api.offering4ai.com`?

### Security
- Which secrets belong in Secret Manager first?
- Do we want stricter CORS once the final domain is live?
- When should public feed rate limiting be tightened?

### Data
- When should Alembic or another migration tool replace startup schema creation?
- Do we need audit tables before real payouts exist?
- How long should public idea history remain immutable?

### Operations
- Which alerts are mandatory for the first public launch?
- Do we want daily or hourly DB backups?
- What is the rollback plan for failed deploys?

## Tomorrow’s likely first move

If the goal is practical launch speed, tomorrow should start with:
1. buy and point `offering4ai.com`
2. deploy the VM path publicly
3. verify HTTPS, sitemap, AI manifest, MCP, and public feed on the live domain
4. then decide whether managed migration is worth the extra cost now or later
