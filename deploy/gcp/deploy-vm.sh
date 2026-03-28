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
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
JWT_SECRET="${JWT_SECRET:-}"
EMAIL_DELIVERY_MODE="${EMAIL_DELIVERY_MODE:-}"
EMAIL_FROM_ADDRESS="${EMAIL_FROM_ADDRESS:-}"
SMTP_HOST="${SMTP_HOST:-}"
SMTP_PORT="${SMTP_PORT:-}"
SMTP_USERNAME="${SMTP_USERNAME:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"
SMTP_USE_TLS="${SMTP_USE_TLS:-}"
SMTP_USE_SSL="${SMTP_USE_SSL:-}"
REGISTRATION_ENABLED="${REGISTRATION_ENABLED:-}"
APP_DIR="${APP_DIR:-/opt/offering4ai}"
SSH_KEY_FILE="${SSH_KEY_FILE:-}"
TRUSTED_HOSTS="${TRUSTED_HOSTS:-}"

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

read_remote_env_value() {
  local key="$1"
  local current_env_path="${APP_DIR}/.env"
  gcloud compute ssh "${INSTANCE_NAME}" \
    --project "${PROJECT_ID}" \
    --zone "${ZONE}" \
    ${SSH_KEY_FILE:+--ssh-key-file "${SSH_KEY_FILE}"} \
    --command "sudo test -f '${current_env_path}' && sudo awk -F= '/^${key}=/{sub(/^[^=]*=/, \"\"); print; exit}' '${current_env_path}' || true" \
    2>/dev/null || true
}

if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  POSTGRES_PASSWORD="$(read_remote_env_value POSTGRES_PASSWORD)"
fi
if [[ -z "${JWT_SECRET}" ]]; then
  JWT_SECRET="$(read_remote_env_value JWT_SECRET)"
fi
if [[ -z "${EMAIL_DELIVERY_MODE}" ]]; then
  EMAIL_DELIVERY_MODE="$(read_remote_env_value EMAIL_DELIVERY_MODE)"
fi
if [[ -z "${EMAIL_FROM_ADDRESS}" ]]; then
  EMAIL_FROM_ADDRESS="$(read_remote_env_value EMAIL_FROM_ADDRESS)"
fi
if [[ -z "${SMTP_HOST}" ]]; then
  SMTP_HOST="$(read_remote_env_value SMTP_HOST)"
fi
if [[ -z "${SMTP_PORT}" ]]; then
  SMTP_PORT="$(read_remote_env_value SMTP_PORT)"
fi
if [[ -z "${SMTP_USERNAME}" ]]; then
  SMTP_USERNAME="$(read_remote_env_value SMTP_USERNAME)"
fi
if [[ -z "${SMTP_PASSWORD}" ]]; then
  SMTP_PASSWORD="$(read_remote_env_value SMTP_PASSWORD)"
fi
if [[ -z "${SMTP_USE_TLS}" ]]; then
  SMTP_USE_TLS="$(read_remote_env_value SMTP_USE_TLS)"
fi
if [[ -z "${SMTP_USE_SSL}" ]]; then
  SMTP_USE_SSL="$(read_remote_env_value SMTP_USE_SSL)"
fi
if [[ -z "${REGISTRATION_ENABLED}" ]]; then
  REGISTRATION_ENABLED="$(read_remote_env_value REGISTRATION_ENABLED)"
fi
if [[ -z "${POSTGRES_PASSWORD}" ]]; then
  POSTGRES_PASSWORD="$(openssl rand -hex 16)"
fi
if [[ -z "${JWT_SECRET}" ]]; then
  JWT_SECRET="$(openssl rand -hex 32)"
fi
if [[ -z "${EMAIL_DELIVERY_MODE}" ]]; then
  EMAIL_DELIVERY_MODE="log"
fi
if [[ -z "${EMAIL_FROM_ADDRESS}" ]]; then
  EMAIL_FROM_ADDRESS="no-reply@offering4ai.com"
fi
if [[ -z "${SMTP_PORT}" ]]; then
  SMTP_PORT="587"
fi
if [[ -z "${SMTP_USE_TLS}" ]]; then
  SMTP_USE_TLS="true"
fi
if [[ -z "${SMTP_USE_SSL}" ]]; then
  SMTP_USE_SSL="false"
fi
if [[ -z "${REGISTRATION_ENABLED}" ]]; then
  if [[ "${EMAIL_DELIVERY_MODE}" == "smtp" && -n "${SMTP_HOST}" ]]; then
    REGISTRATION_ENABLED="true"
  else
    REGISTRATION_ENABLED="false"
  fi
fi

CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-${DEFAULT_CORS_ORIGINS}}"
PUBLIC_API_BASE_URL="${PUBLIC_API_BASE_URL:-${PUBLIC_BASE_URL}}"
PUBLIC_SITE_URL="${PUBLIC_SITE_URL:-${RUNTIME_SITE_URL}}"
if [[ -n "${TRUSTED_HOSTS}" ]]; then
  TRUSTED_HOSTS="${TRUSTED_HOSTS},localhost,127.0.0.1,testserver"
fi

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
TRUSTED_HOSTS=${TRUSTED_HOSTS}
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
EMAIL_DELIVERY_MODE=${EMAIL_DELIVERY_MODE}
EMAIL_FROM_ADDRESS=${EMAIL_FROM_ADDRESS}
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USERNAME=${SMTP_USERNAME}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_USE_TLS=${SMTP_USE_TLS}
SMTP_USE_SSL=${SMTP_USE_SSL}
REGISTRATION_ENABLED=${REGISTRATION_ENABLED}
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
  ${SSH_KEY_FILE:+--ssh-key-file "${SSH_KEY_FILE}"} \
  --command 'mkdir -p /tmp/offering4ai-deploy' >/dev/null

gcloud compute scp \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  ${SSH_KEY_FILE:+--ssh-key-file "${SSH_KEY_FILE}"} \
  "${DEPLOY_TMP_DIR}/.env" \
  "${DEPLOY_TMP_DIR}/docker-compose.yml" \
  "${DEPLOY_TMP_DIR}/Caddyfile" \
  "${DEPLOY_TMP_DIR}/bootstrap-vm.sh" \
  "${INSTANCE_NAME}:/tmp/offering4ai-deploy/" >/dev/null

printf 'Bootstrapping VM services...\n'
gcloud compute ssh "${INSTANCE_NAME}" \
  --project "${PROJECT_ID}" \
  --zone "${ZONE}" \
  ${SSH_KEY_FILE:+--ssh-key-file "${SSH_KEY_FILE}"} \
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
