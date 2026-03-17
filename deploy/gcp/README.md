# Offering4AI GCP Deployment Assets

This folder now supports two Google Cloud deployment paths.

## Recommended path for lowest cost

Use `deploy-vm.sh`.

That path creates a single `e2-micro` Ubuntu VM, pushes your images to Artifact Registry, and runs the whole stack with Docker Compose:
- `caddy`
- `migrate`
- `frontend`
- `api`
- `worker`
- `postgres`
- `redis`

Why this is the cheapest MVP:
- one small VM instead of multiple managed services
- full containerized stack
- same architecture as local Docker Compose
- simple DNS story with one public IP

Tradeoff:
- you operate Postgres and Redis yourself
- backups, patching, and uptime are your responsibility

## Managed upgrade path

Use `deploy-cloud-run.sh`.

That path is cleaner operationally, but not the cheapest because it expects:
- a one-off Cloud Run migration job
- Cloud Run for frontend, API, worker
- Cloud SQL for PostgreSQL
- Memorystore for Redis
- optional VPC connector for private IP access

## Files

- `build-and-push.sh` — builds and pushes all images to Artifact Registry
- `deploy-vm.sh` — cheapest-path deployment to a single Compute Engine VM
- `deploy-cloud-run.sh` — managed deployment to Cloud Run services
- `docker-compose.vm.yml` — production Compose bundle used on the VM
- `Caddyfile` — reverse proxy and HTTPS entrypoint for the VM path
- `remote/bootstrap-vm.sh` — installs Docker on the VM and starts the stack
- `cloudrun-api.env.example` — API and worker env template for Cloud Run
- `cloudrun-frontend.env.example` — frontend env template for Cloud Run

## Fastest cheapest deploy

```bash
PROJECT_ID=your-gcp-project \
ZONE=europe-west1-b \
SITE_ADDRESS=:80 \
./deploy/gcp/deploy-vm.sh
```

If you have already pointed a real domain at the VM, use:

```bash
PROJECT_ID=your-gcp-project \
ZONE=europe-west1-b \
SITE_ADDRESS=offering4ai.com \
SITE_URL=https://offering4ai.com \
./deploy/gcp/deploy-vm.sh
```

## Cloud Run deploy

```bash
PROJECT_ID=your-gcp-project \
REGION=europe-west1 \
API_ENV_FILE=deploy/gcp/cloudrun-api.env.example \
FRONTEND_ENV_FILE=deploy/gcp/cloudrun-frontend.env.example \
./deploy/gcp/deploy-cloud-run.sh
```

## Notes

- The frontend image is a small nginx runtime image built from a locally generated `dist` bundle.
- The frontend reads runtime config from `env.js`, so you can reuse the same image across environments.
- The API now supports configurable CORS via `CORS_ALLOWED_ORIGINS`.
