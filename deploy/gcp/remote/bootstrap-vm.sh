#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/offering4ai}"
REGISTRY_HOST="${REGISTRY_HOST:?Set REGISTRY_HOST}"
DEPLOY_DIR="${DEPLOY_DIR:-/tmp/offering4ai-deploy}"

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

systemctl enable --now docker

mkdir -p "${APP_DIR}"
cp "${DEPLOY_DIR}/.env" "${APP_DIR}/.env"
cp "${DEPLOY_DIR}/docker-compose.yml" "${APP_DIR}/docker-compose.yml"
cp "${DEPLOY_DIR}/Caddyfile" "${APP_DIR}/Caddyfile"
chmod 600 "${APP_DIR}/.env"

ACCESS_TOKEN="$(curl -fsSL -H 'Metadata-Flavor: Google' \
  'http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

echo "${ACCESS_TOKEN}" | docker login -u oauth2accesstoken --password-stdin "https://${REGISTRY_HOST}"

docker compose -f "${APP_DIR}/docker-compose.yml" --env-file "${APP_DIR}/.env" pull
docker compose -f "${APP_DIR}/docker-compose.yml" --env-file "${APP_DIR}/.env" up -d --remove-orphans
docker image prune -f >/dev/null || true
