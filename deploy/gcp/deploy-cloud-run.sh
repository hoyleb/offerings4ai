#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
REPOSITORY="${REPOSITORY:-offering4ai}"
TAG="${TAG:-latest}"
SITE_URL="${SITE_URL:-https://offering4ai.com}"
API_ENV_FILE="${API_ENV_FILE:-${SCRIPT_DIR}/cloudrun-api.env.example}"
FRONTEND_ENV_FILE="${FRONTEND_ENV_FILE:-${SCRIPT_DIR}/cloudrun-frontend.env.example}"
API_SERVICE="${API_SERVICE:-offering4ai-api}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-offering4ai-frontend}"
WORKER_SERVICE="${WORKER_SERVICE:-offering4ai-worker}"
MIGRATION_JOB="${MIGRATION_JOB:-offering4ai-migrate}"
VPC_CONNECTOR="${VPC_CONNECTOR:-}"

REGISTRY_HOST="${REGION}-docker.pkg.dev"
API_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-api:${TAG}"
WORKER_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-worker:${TAG}"
FRONTEND_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-frontend:${TAG}"

printf 'Enabling required Cloud Run APIs...\n'
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  PROJECT_ID="${PROJECT_ID}" \
  REGION="${REGION}" \
  REPOSITORY="${REPOSITORY}" \
  TAG="${TAG}" \
  SITE_URL="${SITE_URL}" \
  FRONTEND_BUILD_API_BASE_URL="${FRONTEND_BUILD_API_BASE_URL:-}" \
  "${SCRIPT_DIR}/build-and-push.sh"
fi

network_flags=()
if [[ -n "${VPC_CONNECTOR}" ]]; then
  network_flags+=(--vpc-connector "${VPC_CONNECTOR}" --vpc-egress private-ranges-only)
fi

printf 'Deploying migration job...\n'
gcloud run jobs deploy "${MIGRATION_JOB}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${API_IMAGE}" \
  --command python \
  --args -m,app.migrations.cli,upgrade \
  --cpu 1 \
  --memory 512Mi \
  --max-retries 1 \
  --tasks 1 \
  --env-vars-file "${API_ENV_FILE}" \
  "${network_flags[@]}"

printf 'Executing migration job...\n'
gcloud run jobs execute "${MIGRATION_JOB}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --wait

printf 'Deploying API service...\n'
gcloud run deploy "${API_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${API_IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --max-instances 3 \
  --env-vars-file "${API_ENV_FILE}" \
  "${network_flags[@]}"

API_URL="$(gcloud run services describe "${API_SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
printf 'API URL: %s\n' "${API_URL}"

printf 'Deploying frontend service...\n'
temp_frontend_env="$(mktemp)"
cp "${FRONTEND_ENV_FILE}" "${temp_frontend_env}"
if ! grep -q '^RUNTIME_API_BASE_URL=' "${temp_frontend_env}"; then
  printf '\nRUNTIME_API_BASE_URL=%s\n' "${API_URL}" >> "${temp_frontend_env}"
fi
if ! grep -q '^RUNTIME_SITE_URL=' "${temp_frontend_env}"; then
  printf 'RUNTIME_SITE_URL=%s\n' "${SITE_URL}" >> "${temp_frontend_env}"
fi

gcloud run deploy "${FRONTEND_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${FRONTEND_IMAGE}" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 256Mi \
  --max-instances 3 \
  --env-vars-file "${temp_frontend_env}"
rm -f "${temp_frontend_env}"

printf 'Deploying worker service...\n'
gcloud run deploy "${WORKER_SERVICE}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --image "${WORKER_IMAGE}" \
  --platform managed \
  --no-allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 1 \
  --max-instances 1 \
  --command python \
  --args -m,app.worker_service \
  --env-vars-file "${API_ENV_FILE}" \
  "${network_flags[@]}"

FRONTEND_URL="$(gcloud run services describe "${FRONTEND_SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"

cat <<EOT
Cloud Run deployment complete:
- Frontend: ${FRONTEND_URL}
- API: ${API_URL}
- Worker: ${WORKER_SERVICE}

If you later attach a custom domain, update:
- PUBLIC_API_BASE_URL in ${API_ENV_FILE}
- PUBLIC_SITE_URL and CORS_ALLOWED_ORIGINS in ${API_ENV_FILE}
- RUNTIME_SITE_URL in ${FRONTEND_ENV_FILE}
EOT
