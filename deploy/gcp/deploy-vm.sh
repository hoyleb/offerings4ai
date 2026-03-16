#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
ZONE="${ZONE:-europe-west1-b}"
REGION="${REGION:-${ZONE%-*}}"
REPOSITORY="${REPOSITORY:-offering4ai}"
TAG="${TAG:-latest}"
INSTANCE_NAME="${INSTANCE_NAME:-offering4ai-vm}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-micro}"
BOOT_DISK_SIZE_GB="${BOOT_DISK_SIZE_GB:-20}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-offering4ai-vm}"
SITE_ADDRESS="${SITE_ADDRESS:-:80}"
SITE_URL="${SITE_URL:-}"
POSTGRES_DB="${POSTGRES_DB:-offering4ai}"
POSTGRES_USER="${POSTGRES_USER:-offering4ai}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -hex 16)}"
JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
APP_DIR="${APP_DIR:-/opt/offering4ai}"

REGISTRY_HOST="${REGION}-docker.pkg.dev"
API_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-api:${TAG}"
WORKER_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-worker:${TAG}"
FRONTEND_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-frontend:${TAG}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

printf 'Enabling required GCP APIs...\n'
gcloud services enable \
  compute.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  --project "${PROJECT_ID}" >/dev/null

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  PROJECT_ID="${PROJECT_ID}" \
  REGION="${REGION}" \
  REPOSITORY="${REPOSITORY}" \
  TAG="${TAG}" \
  SITE_URL="${SITE_URL:-https://offering4ai.com}" \
  FRONTEND_BUILD_API_BASE_URL="${FRONTEND_BUILD_API_BASE_URL:-}" \
  "${SCRIPT_DIR}/build-and-push.sh"
fi

if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  printf 'Creating VM service account %s...\n' "${SERVICE_ACCOUNT_EMAIL}"
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project "${PROJECT_ID}" \
    --display-name "Offering4AI VM" >/dev/null
fi

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role roles/artifactregistry.reader >/dev/null

if ! gcloud compute firewall-rules describe offering4ai-public --project "${PROJECT_ID}" >/dev/null 2>&1; then
  printf 'Creating firewall rule offering4ai-public...\n'
  gcloud compute firewall-rules create offering4ai-public \
    --project "${PROJECT_ID}" \
    --allow tcp:22,tcp:80,tcp:443 \
    --target-tags offering4ai-public \
    --description 'SSH, HTTP, and HTTPS for Offering4AI' >/dev/null
fi

if ! gcloud compute instances describe "${INSTANCE_NAME}" --project "${PROJECT_ID}" --zone "${ZONE}" >/dev/null 2>&1; then
  printf 'Creating VM %s...\n' "${INSTANCE_NAME}"
  gcloud compute instances create "${INSTANCE_NAME}" \
    --project "${PROJECT_ID}" \
    --zone "${ZONE}" \
    --machine-type "${MACHINE_TYPE}" \
    --boot-disk-size "${BOOT_DISK_SIZE_GB}GB" \
    --image-family ubuntu-2204-lts \
    --image-project ubuntu-os-cloud \
    --tags offering4ai-public \
    --service-account "${SERVICE_ACCOUNT_EMAIL}" \
    --scopes cloud-platform >/dev/null
fi

EXTERNAL_IP="$(gcloud compute instances describe "${INSTANCE_NAME}" \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  --format='value(networkInterfaces[0].accessConfigs[0].natIP)')"

if [[ -n "${SITE_URL}" ]]; then
  PUBLIC_BASE_URL="${SITE_URL%/}"
  RUNTIME_SITE_URL="${SITE_URL%/}"
  DEFAULT_CORS_ORIGINS="${SITE_URL%/}"
else
  PUBLIC_BASE_URL="http://${EXTERNAL_IP}"
  RUNTIME_SITE_URL="http://${EXTERNAL_IP}"
  DEFAULT_CORS_ORIGINS="http://${EXTERNAL_IP}"
fi

CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-${DEFAULT_CORS_ORIGINS}}"
PUBLIC_API_BASE_URL="${PUBLIC_API_BASE_URL:-${PUBLIC_BASE_URL}}"
PUBLIC_SITE_URL="${PUBLIC_SITE_URL:-${RUNTIME_SITE_URL}}"

DEPLOY_TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${DEPLOY_TMP_DIR}"
}
trap cleanup EXIT

cat > "${DEPLOY_TMP_DIR}/.env" <<EOT
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
REDIS_URL=redis://redis:6379/0
QUEUE_MODE=redis
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8899
PUBLIC_API_BASE_URL=${PUBLIC_API_BASE_URL}
PUBLIC_SITE_URL=${PUBLIC_SITE_URL}
CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRE_MINUTES=1440
PLATFORM_FEE_PERCENT=${PLATFORM_FEE_PERCENT:-10}
EVALUATION_THRESHOLD=${EVALUATION_THRESHOLD:-28}
EVALUATOR_PROVIDER=${EVALUATOR_PROVIDER:-mock}
OPENAI_API_KEY=${OPENAI_API_KEY:-}
OPENAI_MODEL=${OPENAI_MODEL:-gpt-5-mini}
PAYMENT_PROVIDER=${PAYMENT_PROVIDER:-simulated}
DEFAULT_CURRENCY=${DEFAULT_CURRENCY:-USD}
MAX_SUBMISSIONS_PER_HOUR=${MAX_SUBMISSIONS_PER_HOUR:-5}
SIMILARITY_THRESHOLD=${SIMILARITY_THRESHOLD:-0.88}
API_IMAGE=${API_IMAGE}
WORKER_IMAGE=${WORKER_IMAGE}
FRONTEND_IMAGE=${FRONTEND_IMAGE}
SITE_ADDRESS=${SITE_ADDRESS}
RUNTIME_API_BASE_URL=
RUNTIME_SITE_URL=${RUNTIME_SITE_URL}
EOT

cp "${SCRIPT_DIR}/docker-compose.vm.yml" "${DEPLOY_TMP_DIR}/docker-compose.yml"
cp "${SCRIPT_DIR}/Caddyfile" "${DEPLOY_TMP_DIR}/Caddyfile"
cp "${SCRIPT_DIR}/remote/bootstrap-vm.sh" "${DEPLOY_TMP_DIR}/bootstrap-vm.sh"

printf 'Uploading deployment bundle to VM...\n'
gcloud compute ssh "${INSTANCE_NAME}" \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  --command 'mkdir -p /tmp/offering4ai-deploy' >/dev/null

gcloud compute scp \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  "${DEPLOY_TMP_DIR}/.env" \
  "${DEPLOY_TMP_DIR}/docker-compose.yml" \
  "${DEPLOY_TMP_DIR}/Caddyfile" \
  "${DEPLOY_TMP_DIR}/bootstrap-vm.sh" \
  "${INSTANCE_NAME}:/tmp/offering4ai-deploy/" >/dev/null

printf 'Bootstrapping VM services...\n'
gcloud compute ssh "${INSTANCE_NAME}" \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  --command "sudo REGISTRY_HOST='${REGISTRY_HOST}' APP_DIR='${APP_DIR}' DEPLOY_DIR='/tmp/offering4ai-deploy' bash /tmp/offering4ai-deploy/bootstrap-vm.sh"

cat <<EOT
Cheapest-path VM deployment complete:
- Instance: ${INSTANCE_NAME}
- Zone: ${ZONE}
- Public IP: ${EXTERNAL_IP}
- App URL: ${PUBLIC_BASE_URL}

If you later point offering4ai.com at this VM, rerun with:
SITE_ADDRESS=offering4ai.com SITE_URL=https://offering4ai.com PROJECT_ID=${PROJECT_ID} ZONE=${ZONE} ${SCRIPT_DIR}/deploy-vm.sh
EOT
