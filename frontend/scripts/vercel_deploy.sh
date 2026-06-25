#!/usr/bin/env bash
# Deploy WhatSub frontend to Vercel (production).
#
# Prerequisites:
#   1. vercel login   OR   export VERCEL_TOKEN=...
#   2. Root .env has BACKEND_URL=https://whatsub-api.fly.dev
#
# Usage (from repo root):
#   bash frontend/scripts/vercel_deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND="$ROOT/frontend"
ENV_FILE="$ROOT/.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

BACKEND_URL="${BACKEND_URL:-https://whatsub-api.fly.dev}"
export VITE_BACKEND_URL="$BACKEND_URL"

cd "$FRONTEND"
npm run build
npx vercel deploy --prod --yes

echo ""
echo "After deploy, copy the production URL and update root .env:"
echo "  FRONTEND_URL='https://YOUR-PROJECT.vercel.app'"
echo "Then:"
echo "  bash backend/scripts/fly_set_secrets.sh"
echo "  cd backend && fly deploy --depot=false"
