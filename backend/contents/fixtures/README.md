# Benchmark & streaming cache fixtures

벤치마크 랭킹·장르 차트·영화/시리즈 목록을 **API 키 없이** 재현하기 위한 덤프입니다.

| File | Contents | Approx. size |
|------|----------|--------------|
| `benchmark_snapshot.json` | `PlatformBenchmarkSnapshot`, `PlatformGenreStats` | ~30KB |
| `benchmark_streaming_cache.json` | `StreamingCache`, `TitleMeta`, `TitleGenres` | ~600KB |

## Load order (new machine)

`subscriptions` 플랫폼 catalog가 **먼저** 있어야 FK가 맞습니다.

```bash
cd backend
python manage.py migrate
python manage.py loaddata subscriptions/fixtures/subscriptions_catalog.json
python -X utf8 scripts/load_fixture_idempotent.py contents/fixtures/benchmark_snapshot.json
python -X utf8 scripts/load_fixture_idempotent.py contents/fixtures/benchmark_streaming_cache.json 150
```

Verify:

```bash
python manage.py shell -c "from contents.models import PlatformBenchmarkSnapshot, StreamingCache; print(PlatformBenchmarkSnapshot.objects.count(), 'snapshots', StreamingCache.objects.count(), 'cache rows')"
```

## Refresh dumps (after `warm_cache` + `run_benchmark_batch`)

Windows에서 한글/외국어 제목 때문에 `-X utf8` 권장:

```bash
cd backend
python -X utf8 manage.py dumpdata contents.platformbenchmarksnapshot contents.platformgenrestats --indent 2 -o contents/fixtures/benchmark_snapshot.json

python -X utf8 manage.py dumpdata contents.streamingcache contents.titlemeta contents.titlegenres --indent 2 -o contents/fixtures/benchmark_streaming_cache.json
```

또는 캐시만 갱신:

```bash
python manage.py warm_cache --skip-rapidapi
python manage.py run_benchmark_batch --skip-llm
# then dump commands above
```

## Do NOT dump (commit 금지)

- `db.sqlite3` — 로컬 DB 전체
- `accounts.*`, `UserSubscription`, Gmail/SocialToken — 사용자 데이터
- `LLMJudgmentCache` — API로 재생성 가능, 용량·만료 이슈
- `.env` — API 키

## Notes

- 스냅샷 날짜는 덤프 시점 DB 기준 (예: `2026-06-23`).
- `benchmark_streaming_cache.json` 없으면 벤치마크 UI는 동작하지만 **영화/시리즈 필터·목록**이 비어 있을 수 있습니다.
- 아이콘 파일은 `backend/subscriptions/media/` (Git에 포함된 정적 미디어).
