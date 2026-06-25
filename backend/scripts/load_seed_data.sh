#!/usr/bin/env bash
# Apply migrations and load demo/catalog fixtures (Supabase or local SQLite).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${STREAMING_CACHE_ONLY:-}" == "1" ]]; then
  echo "[4/4 only] streaming cache (batched)"
  python -X utf8 scripts/load_fixture_batched.py contents/fixtures/benchmark_streaming_cache.json 150
  python manage.py shell -c "
from contents.models import StreamingCache
print(StreamingCache.objects.count(), 'cache rows')
"
  echo "Streaming cache loaded."
  exit 0
fi

echo "[1/4] migrate"
python manage.py migrate

echo "[2/4] subscriptions catalog"
python manage.py loaddata subscriptions/fixtures/subscriptions_catalog.json

echo "[3/4] benchmark snapshot"
python -X utf8 manage.py loaddata contents/fixtures/benchmark_snapshot.json

echo "[4/4] streaming cache (batched — remote Supabase can be slow)"
python -X utf8 scripts/load_fixture_batched.py contents/fixtures/benchmark_streaming_cache.json 150

echo "[5/5] demo activity (users, community, reviews)"
python manage.py seed_demo --reset

python manage.py shell -c "
from contents.models import PlatformBenchmarkSnapshot, StreamingCache, PlatformUserReview, ContentReaction
from community.models import CommunityPost, CommunityComment
from subscriptions.models import Platform, SubscriptionPlan
from django.contrib.auth import get_user_model
User = get_user_model()
print(
    Platform.objects.count(), 'platforms,',
    SubscriptionPlan.objects.count(), 'plans,',
    PlatformBenchmarkSnapshot.objects.count(), 'snapshots,',
    StreamingCache.objects.count(), 'cache rows,',
    User.objects.filter(username__startswith='demo_').count(), 'demo users,',
    CommunityPost.objects.count(), 'posts,',
    CommunityComment.objects.count(), 'comments,',
    PlatformUserReview.objects.count(), 'platform reviews,',
    ContentReaction.objects.count(), 'content reactions,',
)
"

echo "Seed data loaded."
