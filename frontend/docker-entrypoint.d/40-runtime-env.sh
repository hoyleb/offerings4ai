#!/bin/sh
set -eu

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

api_base_url="$(json_escape "${RUNTIME_API_BASE_URL:-}")"
site_url="$(json_escape "${RUNTIME_SITE_URL:-}")"

cat > /usr/share/nginx/html/env.js <<EOT
window.__APP_CONFIG__ = {
  API_BASE_URL: "${api_base_url}",
  SITE_URL: "${site_url}"
};
EOT
