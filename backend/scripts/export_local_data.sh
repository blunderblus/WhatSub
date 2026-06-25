#!/usr/bin/env bash
# Export optional user/auth data from the current DB (e.g. local SQLite → Supabase loaddata).
# Catalog/benchmark rows are already in fixtures; use this only for accounts you want to keep.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${1:-exports/local_user_data.json}"
mkdir -p "$(dirname "$OUT")"

python manage.py dumpdata \
  accounts \
  socialaccount \
  subscriptions.usersubscription \
  --indent 2 \
  -o "$OUT"

echo "Wrote $OUT"
