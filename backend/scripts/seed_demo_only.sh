#!/usr/bin/env bash
# Apply demo activity only (users, community, reviews) — catalog/benchmark must exist.
set -euo pipefail
cd "$(dirname "$0")/.."

python manage.py seed_demo --reset
echo "Demo activity applied."
