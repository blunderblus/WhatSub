#!/usr/bin/env bash
# Set Fly.io secrets from project-root .env (run once after fly launch).
# Usage: bash scripts/fly_set_secrets.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="$ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

: "${SECRET_KEY:?SECRET_KEY missing in .env}"
: "${FRONTEND_URL:?FRONTEND_URL missing — set to Vercel URL when ready, or placeholder}"
: "${BACKEND_URL:?BACKEND_URL missing — set to https://YOUR_APP.fly.dev}"
: "${DATABASE_URL:?DATABASE_URL missing — Supabase URI for production}"

fly secrets set \
  SECRET_KEY="$SECRET_KEY" \
  DATABASE_URL="$DATABASE_URL" \
  FRONTEND_URL="$FRONTEND_URL" \
  BACKEND_URL="$BACKEND_URL" \
  TMDB_API_KEY="${TMDB_API_KEY:-}" \
  WATCHMODE_API_KEY="${WATCHMODE_API_KEY:-}" \
  RAPID_API_KEY="${RAPID_API_KEY:-}" \
  AI_API_KEY="${AI_API_KEY:-}" \
  AI_API_BASE="${AI_API_BASE:-}" \
  AI_MODEL="${AI_MODEL:-}" \
  AI_VISION_MODEL="${AI_VISION_MODEL:-}" \
  AI_VISION_API_BASE="${AI_VISION_API_BASE:-}" \
  GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}" \
  GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}" \
  ALLOWED_HOSTS="$(python - <<'PY'
from urllib.parse import urlparse
import os
print(urlparse(os.environ["BACKEND_URL"]).hostname or "")
PY
)"

echo "Fly secrets updated."
