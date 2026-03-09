#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

printf 'Building frontend bundle...\n'
cd "${REPO_ROOT}/frontend"
npm install
npm run build

printf 'Starting Docker Compose stack...\n'
cd "${REPO_ROOT}"
DOCKER_BUILDKIT=0 COMPOSE_DOCKER_CLI_BUILD=0 docker compose up --build -d
