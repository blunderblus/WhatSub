#!/usr/bin/env bash
# Set Fly.io secrets from project-root .env (run once after fly launch).
#
# Supabase URI: set FLY_DATABASE_URL in .env (local DATABASE_URL can stay commented).
#   Fly runtime: Transaction pooler port 6543 OK
#
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

DATABASE_URL="${FLY_DATABASE_URL:-${DATABASE_URL:-}}"

: "${SECRET_KEY:?SECRET_KEY missing in .env}"
: "${FRONTEND_URL:?FRONTEND_URL missing — set to Vercel URL when ready, or placeholder}"
: "${BACKEND_URL:?BACKEND_URL missing — set to https://YOUR_APP.fly.dev}"
if [[ -z "$DATABASE_URL" || "$DATABASE_URL" == *YOUR_PASSWORD* ]]; then
  echo "FLY_DATABASE_URL missing or placeholder in .env" >&2
  echo "  Supabase Dashboard → Connect → URI 복사 (호스트 aws-0/aws-1 Dashboard 값 그대로)" >&2
  echo "  GitHub Actions seed에 성공한 DATABASE_URL secret 과 동일하게 맞출 것" >&2
  echo "  wrong host →: tenant/user postgres.[ref] not found" >&2
  exit 1
fi

fly secrets set --stage \
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
  GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"

echo "Fly secrets staged (not deployed yet)."
echo "Next: fly deploy --depot=false"
