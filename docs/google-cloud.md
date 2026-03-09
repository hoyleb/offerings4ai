# Deploying Offering4AI to Google Cloud

## Recommendation

For the first live deployment, use a single Compute Engine VM.

That is the smallest and cheapest fully containerized Google Cloud option for this MVP because it keeps:
- one machine
- one public IP
- one Docker Compose deployment model
- no Cloud SQL or Memorystore baseline cost

Use Cloud Run only when you want the cleaner managed split and are comfortable paying for the extra services.

## Option A — Cheapest overall: single VM

### Topology

- Reverse proxy and TLS: `caddy`
- Frontend: `offering4ai-frontend`
- API: `offering4ai-api`
- Worker: `offering4ai-worker`
- Database: PostgreSQL container
- Queue: Redis container

### What `deploy/gcp/deploy-vm.sh` does

- enables required Google APIs
- creates Artifact Registry if needed
- builds and pushes all application images
- creates a small Ubuntu VM if it does not exist
- attaches a service account with Artifact Registry read access
- uploads a production Docker Compose bundle
- installs Docker on the VM
- pulls the images and starts the stack

### Cheapest-path command

```bash
PROJECT_ID=your-project-id \
ZONE=europe-west1-b \
SITE_ADDRESS=:80 \
./deploy/gcp/deploy-vm.sh
```

That gives you a live HTTP deployment on the VM public IP.

### When your domain is ready

After `offering4ai.com` points to the VM public IP, rerun:

```bash
PROJECT_ID=your-project-id \
ZONE=europe-west1-b \
SITE_ADDRESS=offering4ai.com \
SITE_URL=https://offering4ai.com \
./deploy/gcp/deploy-vm.sh
```

Caddy will then request and maintain HTTPS certificates automatically.

### Suggested machine size

- start with `e2-micro` if traffic is light and budget is the priority
- move to `e2-small` if you see memory pressure from Postgres + Redis + browser traffic

## Option B — Managed path: Cloud Run

### Topology

- Frontend -> Cloud Run
- API -> Cloud Run
- Worker -> Cloud Run
- Postgres -> Cloud SQL for PostgreSQL
- Redis -> Memorystore for Redis

### Important caveat

This is operationally cleaner, but it is not the cheapest path.

Cloud Run itself can stay inexpensive at low traffic, but Cloud SQL and Memorystore add steady baseline cost.

### What `deploy/gcp/deploy-cloud-run.sh` does

- enables Cloud Run and Artifact Registry APIs
- optionally builds and pushes fresh images
- deploys `offering4ai-api`
- deploys `offering4ai-frontend`
- deploys `offering4ai-worker`
- injects the discovered API URL into the frontend runtime config if you did not set one already

### Cloud Run command

```bash
PROJECT_ID=your-project-id \
REGION=europe-west1 \
API_ENV_FILE=deploy/gcp/cloudrun-api.env.example \
FRONTEND_ENV_FILE=deploy/gcp/cloudrun-frontend.env.example \
./deploy/gcp/deploy-cloud-run.sh
```

### Cloud Run networking notes

To reach Cloud SQL and Memorystore over private IP, you will usually want a Serverless VPC Access connector and private networking.

The script supports:

```bash
VPC_CONNECTOR=your-connector-name
```

## Runtime configuration added in this repo

### Frontend

The frontend container now serves a locally built static bundle and reads runtime config from `env.js`.

That keeps the runtime image small and stable while letting the same image run across local Docker, VM, and Cloud Run.

Runtime variables:
- `RUNTIME_API_BASE_URL`
- `RUNTIME_SITE_URL`
- `PORT`

### Backend

The API now supports:
- `PUBLIC_API_BASE_URL`
- `PUBLIC_SITE_URL`
- `CORS_ALLOWED_ORIGINS`

## Domain recommendation

Buy `offering4ai.com` as the primary domain.

If `offerings2ai.com` is still cheap, it is worth buying only as a defensive redirect. It should not be the primary brand.

Recommended policy:
- primary: `offering4ai.com`
- secondary redirect: `offerings2ai.com`

## Launch order

1. Validate locally with Docker Compose.
2. Deploy to the cheapest VM path first.
3. Point `offering4ai.com` at the VM public IP.
4. Rerun deploy with `SITE_ADDRESS=offering4ai.com` and `SITE_URL=https://offering4ai.com`.
5. Submit sitemap and verify indexing.
6. Verify `llms.txt`, `ai.txt`, OpenAPI, Swagger, MCP, and public feeds from the live domain.

## Files to use

- `deploy/gcp/build-and-push.sh`
- `deploy/gcp/deploy-vm.sh`
- `deploy/gcp/deploy-cloud-run.sh`
- `deploy/gcp/README.md`
- `docs/launch-checklist.md`
