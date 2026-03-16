# Offering4AI

Offering4AI is the product name. Human creators submit ideas, AI evaluators score them, and accepted ideas trigger a logged reward flow with platform fee deduction.

The product is built to be machine-readable first:
- `frontend`: React + TypeScript interface for humans and public AI-facing discovery
- `backend`: FastAPI API with Swagger and OpenAPI
- `mcp`: public Model Context Protocol server mounted inside the API service
- `worker`: Redis-backed evaluation worker
- `postgres`: idea, evaluation, and payout persistence
- `redis`: evaluation queue

## Local Ports

To avoid conflicts with other projects, the stack uses:
- Frontend: `http://localhost:5188`
- API: `http://localhost:8899`
- Postgres: `localhost:5544`
- Redis: `localhost:6399`

## Public AI Surfaces

These are intentionally public and machine-readable:
- Swagger UI: `http://localhost:8899/docs`
- OpenAPI JSON: `http://localhost:8899/openapi.json`
- Project profile: `http://localhost:8899/api/public/about`
- Submission schema: `http://localhost:8899/api/public/submission-schema`
- Evaluation rubric: `http://localhost:8899/api/public/evaluation-rubric`
- Public idea feed: `http://localhost:8899/api/public/ideas/feed`
- AI manifest: `http://localhost:8899/.well-known/ai-manifest.json`
- MCP descriptor: `http://localhost:8899/.well-known/mcp.json`
- MCP SSE endpoint: `http://localhost:8899/mcp/sse`

## Safety Guardrails

To reduce prompt-hacking risk for visiting agents:
- submissions are screened for prompt-injection and payout-manipulation patterns at intake
- suspicious submissions are rejected before they enter the public idea pool
- new creator accounts must verify their email address before login or idea submission
- browser sessions use `HttpOnly` auth cookies plus CSRF protection instead of frontend token storage
- production API traffic enforces trusted hosts, HTTPS-only behavior, and request rate limits
- the evaluator prompt explicitly treats all idea fields as untrusted data
- the public feed excludes duplicate-flagged submissions

## Public Disclosure

This MVP treats idea discovery as public-by-design:
- submissions that pass intake safety screening and duplicate checks become publicly discoverable, even if the evaluator later rejects them commercially
- creator contact email and optional payout destination are exposed in the public feed so future buyers can find the creator again
- do not submit private, secret, or embargoed material

## MVP Features

- Creator registration, email verification, and login
- Structured idea submission with AI-decided reward framing
- Duplicate fingerprint detection
- Similarity scoring for spam and duplicate risk
- Public machine-readable catalog and AI manifest
- Public MCP server for agent discovery and feed access
- Redis evaluation queue
- Deterministic mock evaluator by default
- Simulated payout ledger for accepted ideas
- Dashboard with submission outcomes and reward totals
- Cloud Run-friendly container port support
- Worker health service mode for HTTP-based runtimes

## Quick Start

### Prerequisites

- Docker
- Docker Compose (`docker compose`)

### Start the stack

```bash
./scripts/local-up.sh
```

What this now does:
- builds the frontend bundle
- starts a one-off migration container before the API and worker boot
- starts the application stack only after the schema is current

### Open the app

- Frontend: `http://localhost:5188`
- API health: `http://localhost:8899/health`

### Stop the stack

```bash
./scripts/local-down.sh
```

### Reset local data

```bash
docker compose down -v
./scripts/local-up.sh
```

## Validation

Run the smallest sufficient local checks:

### Backend

```bash
cd backend
python -m app.migrations.cli current
ruff check .
ruff format .
pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run build
npm run test:e2e
```

Notes:
- The Docker stack should already be running on `5188` and `8899` before E2E.
- HTML reports are written under `frontend/output/playwright/report`.

## Configuration

Environment values live in `.env`.

Key settings:
- `EVALUATOR_PROVIDER=mock` uses deterministic local scoring
- `EVALUATOR_PROVIDER=openai` enables LLM evaluation when `OPENAI_API_KEY` is set
- `EVALUATION_THRESHOLD=28` controls acceptance cutoff
- `PLATFORM_FEE_PERCENT=10` sets the platform fee
- `QUEUE_MODE=redis` uses the worker queue
- `EMAIL_DELIVERY_MODE=log` prints verification emails to the API logs for local development
- `EMAIL_DELIVERY_MODE=smtp` enables real verification emails via SMTP
- `EMAIL_FROM_ADDRESS` controls the sender address for verification mail
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, and `SMTP_USE_SSL` configure SMTP delivery
- `EMAIL_VERIFY_TOKEN_EXPIRE_MINUTES` sets how long a verification link remains valid
- `PUBLIC_API_BASE_URL` sets the externally visible API base URL for manifests and MCP consumers
- `PUBLIC_SITE_URL` sets the public site URL for deployment metadata, docs, and verification links
- `CORS_ALLOWED_ORIGINS` sets the allowed browser origins for the API
- `TRUSTED_HOSTS` sets the allowed `Host` headers for the API; when omitted, the app derives them from the public URLs plus localhost
- `ENFORCE_HTTPS=true` forces HTTPS in production and rejects insecure production requests
- `SESSION_COOKIE_NAME`, `CSRF_COOKIE_NAME`, and `CSRF_HEADER_NAME` control the browser session and CSRF plumbing
- `AUTH_RATE_LIMIT_COUNT`, `WRITE_RATE_LIMIT_COUNT`, and `PUBLIC_FEED_RATE_LIMIT_COUNT` tune the built-in request throttles
- `PORT` is honored by API and frontend containers for Cloud Run-style platforms
- `RUNTIME_API_BASE_URL` lets the frontend point at a separate API origin without rebuilding; leave it blank when the frontend reverse-proxies `/api`, `/docs`, `/.well-known`, and `/mcp` on the same origin
- `RUNTIME_SITE_URL` lets the frontend expose the live site URL at runtime

## Project Structure

```text
backend/
  app/
    api/routes/
    core/
    services/
    mcp_server.py
    worker.py
    worker_service.py
  tests/
frontend/
  public/
  src/
deploy/
  gcp/
docs/
docker-compose.yml
```

## Google Cloud Deployment

Helpers and examples live in `deploy/gcp/`.

Recommended first production deployment:
- cheapest overall: `deploy/gcp/deploy-vm.sh` on a single `e2-micro` VM
- managed upgrade path: `deploy/gcp/deploy-cloud-run.sh`

Important files:
- `deploy/gcp/build-and-push.sh`
- `deploy/gcp/deploy-vm.sh`
- `deploy/gcp/deploy-cloud-run.sh`
- `deploy/gcp/cloudrun-api.env.example`
- `deploy/gcp/cloudrun-frontend.env.example`
- `docs/google-cloud.md`
- `docs/launch-checklist.md`
- `docs/cloud-migration-plan.md`

## Important MVP Notes

- Payouts are simulated, not real Stripe or on-chain transfers.
- The default evaluator is deterministic so local tests are stable.
- OpenAI-based evaluation is supported by config, but disabled by default.
- Legal and IP handling is represented as an ownership record string for MVP purposes.
- The API no longer mutates schema at startup; run the migration command or deploy flow first.
- Production deployment should move Postgres and Redis to managed services.

## Next Steps

Recommended next improvements:
- replace simulated payouts with Stripe Connect or wallet integration
- add admin review and audit console
- add embeddings-based novelty and near-duplicate scoring
- add signed legal artifacts for acceptance and transfer events
- add a budget model for competing AI buyers
