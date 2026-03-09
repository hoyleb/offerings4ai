#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-europe-west1}"
REPOSITORY="${REPOSITORY:-offering4ai}"
TAG="${TAG:-latest}"
SITE_URL="${SITE_URL:-https://offering4ai.com}"
FRONTEND_BUILD_API_BASE_URL="${FRONTEND_BUILD_API_BASE_URL:-}"

REGISTRY_HOST="${REGION}-docker.pkg.dev"
API_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-api:${TAG}"
WORKER_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-worker:${TAG}"
FRONTEND_IMAGE="${REGISTRY_HOST}/${PROJECT_ID}/${REPOSITORY}/offering4ai-frontend:${TAG}"

printf 'Enabling Artifact Registry API...\n'
gcloud services enable artifactregistry.googleapis.com --project "${PROJECT_ID}" >/dev/null

if ! gcloud artifacts repositories describe "${REPOSITORY}" \
  --project "${PROJECT_ID}" \
  --location "${REGION}" >/dev/null 2>&1; then
  printf 'Creating Artifact Registry repository %s...\n' "${REPOSITORY}"
  gcloud artifacts repositories create "${REPOSITORY}" \
    --project "${PROJECT_ID}" \
    --location "${REGION}" \
    --repository-format docker \
    --description "Offering4AI container images" >/dev/null
fi

printf 'Configuring Docker auth for %s...\n' "${REGISTRY_HOST}"
gcloud auth configure-docker "${REGISTRY_HOST}" --quiet >/dev/null

printf 'Building backend image...\n'
docker build \
  -t "${API_IMAGE}" \
  -t "${WORKER_IMAGE}" \
  "${REPO_ROOT}/backend"

printf 'Building local frontend bundle...\n'
(
  cd "${REPO_ROOT}/frontend"
  npm install
  VITE_SITE_URL="${SITE_URL}" VITE_API_BASE_URL="${FRONTEND_BUILD_API_BASE_URL}" npm run build
)

printf 'Building frontend image...\n'
docker build \
  -t "${FRONTEND_IMAGE}" \
  "${REPO_ROOT}/frontend"

printf 'Pushing images...\n'
docker push "${API_IMAGE}"
docker push "${WORKER_IMAGE}"
docker push "${FRONTEND_IMAGE}"

cat <<EOT
Built and pushed:
- API_IMAGE=${API_IMAGE}
- WORKER_IMAGE=${WORKER_IMAGE}
- FRONTEND_IMAGE=${FRONTEND_IMAGE}
EOT
