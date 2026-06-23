"""Genre-balanced and platform-targeted cold-start cache warming."""
import logging
import time
from dataclasses import dataclass, field

from django.db.models import Count

from . import tmdb_client
from .benchmark_cache import (
    UNIQUE_TITLE_BUDGET_WARN,
    get_fresh_content,
    is_streaming_cache_fresh,
    resync_streaming_cache_from_content,
    sync_streaming_cache_from_providers,
    sync_streaming_cache_from_tmdb,
    sync_title_genres,
    upsert_title_meta,
)
from .models import MediaType, StreamingCache, WatchmodeUsage

logger = logging.getLogger(__name__)

# TMDB movie genres (18) — excludes TV Movie (10770)
GENRES_MOVIE = [
    28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27, 10402, 9648, 10749, 878, 53, 10752, 37,
]

# TMDB TV genres (16)
GENRES_TV = [
    10759, 16, 35, 80, 99, 18, 10751, 10762, 9648, 10763, 10764, 10765, 10766, 10767, 10768, 37,
]

KR_PLATFORMS_PROVIDER_ID = {
    'TVING': 200,
    'Wavve': 356,
    'Watcha': 97,
}

PLATFORM_WARM_MAX_PAGES = 3
WATCHMODE_SLEEP_SEC = 0.1
# get_streaming_providers -> _augment_with_watchmode: resolve + sources (worst case)
WATCHMODE_HTTP_PER_AVAILABILITY_FETCH = 2

GENRE_LABELS = {
    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
    99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
    27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi',
    53: 'Thriller', 10752: 'War', 37: 'Western', 10759: 'Action & Adventure',
    10762: 'Kids', 10763: 'News', 10764: 'Reality', 10765: 'Sci-Fi & Fantasy',
    10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics',
}


def _watchmode_usage_count():
    row = WatchmodeUsage.objects.filter(month=WatchmodeUsage._current_month()).first()
    return row.count if row else 0


@dataclass
class StageProgress:
    unique_titles: int = 0
    watchmode_http_calls: int = 0
    availability_fetches: int = 0
    availability_failed: int = 0
    skipped_fresh: int = 0
    skipped_session: int = 0
    errors: int = 0


@dataclass
class WarmSession:
    """Shared state across stage 1 and stage 2 within one warm_cache run."""
    availability_fetched: set = field(default_factory=set)


def collect_genre_balanced_titles():
    """Fetch page-1 discover results for every movie/TV genre."""
    unique = {}
    genre_plan = [
        (MediaType.MOVIE, GENRES_MOVIE),
        (MediaType.TV, GENRES_TV),
    ]

    for media_type, genre_ids in genre_plan:
        for genre_id in genre_ids:
            label = GENRE_LABELS.get(genre_id, str(genre_id))
            try:
                data = tmdb_client.discover_by_genre(media_type, genre_id, page=1)
            except Exception as exc:
                logger.error(
                    '[warm_cache] discover failed %s genre %s (%s): %s',
                    media_type, genre_id, label, exc,
                )
                continue

            added = 0
            for item in data.get('results') or []:
                key = (item['id'], media_type)
                if key not in unique:
                    unique[key] = item
                    added += 1

            logger.info(
                '[warm_cache] [stage1-collect] %s genre %s (%s): '
                'fetched %d, new unique %d, total unique %d',
                media_type, genre_id, label,
                len(data.get('results') or []), added, len(unique),
            )

    return unique


def collect_platform_targeted_titles(existing_keys):
    """
    Fetch discover results per KR platform (movie + tv, up to 3 pages each).

    Skips titles already present in ``existing_keys`` from stage 1.
    """
    unique = {}

    for platform_name, provider_id in KR_PLATFORMS_PROVIDER_ID.items():
        for media_type in (MediaType.MOVIE, MediaType.TV):
            for page in range(1, PLATFORM_WARM_MAX_PAGES + 1):
                try:
                    data = tmdb_client.discover_by_provider(media_type, provider_id, page=page)
                except Exception as exc:
                    logger.error(
                        '[warm_cache] discover failed %s provider %s (%s) page %d: %s',
                        media_type, provider_id, platform_name, page, exc,
                    )
                    continue

                added = 0
                for item in data.get('results') or []:
                    key = (item['id'], media_type)
                    if key in existing_keys or key in unique:
                        continue
                    unique[key] = item
                    added += 1

                logger.info(
                    '[warm_cache] [stage2-collect] %s %s page %d: '
                    'fetched %d, new unique %d, stage2 total %d',
                    platform_name, media_type, page,
                    len(data.get('results') or []), added, len(unique),
                )

    return unique


def _refresh_title_metadata(item, media_type):
    tmdb_id = item['id']
    upsert_title_meta(item, media_type)
    sync_title_genres(tmdb_id, media_type, item.get('genre_ids') or [])


def _sync_from_fresh_content_cache(tmdb_id, media_type):
    content = get_fresh_content(tmdb_id)
    if not content or not content.sources_cache:
        return False
    sync_streaming_cache_from_providers(tmdb_id, media_type, content.sources_cache)
    return True


def _warm_streaming_availability(tmdb_id, media_type, skip_rapidapi=False):
    """
    Reuse provider resolution and sync into StreamingCache (Watchmode disabled).
    Falls back to TMDB watch providers when RapidAPI returns empty.
    """
    from .views import get_streaming_providers

    rows_before = StreamingCache.objects.filter(
        tmdb_id=tmdb_id, media_type=media_type, available=True,
    ).count()

    providers = get_streaming_providers(
        tmdb_id, media_type,
        force_refresh=skip_rapidapi,
        skip_rapidapi=skip_rapidapi,
    )
    sync_streaming_cache_from_providers(tmdb_id, media_type, providers)

    rows_after = StreamingCache.objects.filter(
        tmdb_id=tmdb_id, media_type=media_type, available=True,
    ).count()
    has_subs = any(p.get('type') == 'subscription' for p in providers)
    synced = rows_after > rows_before or has_subs

    if not synced:
        synced = sync_streaming_cache_from_tmdb(tmdb_id, media_type)

    return synced


def _count_skippable_titles(title_keys):
    """Estimate how many titles can skip a fresh availability fetch."""
    skippable = 0
    for tmdb_id, media_type in title_keys:
        if is_streaming_cache_fresh(tmdb_id, media_type):
            skippable += 1
        elif get_fresh_content(tmdb_id):
            skippable += 1
    return skippable


def _estimate_watchmode_http_needed(title_keys):
    need_fetch = 0
    for tmdb_id, media_type in title_keys:
        if is_streaming_cache_fresh(tmdb_id, media_type):
            continue
        if get_fresh_content(tmdb_id):
            continue
        need_fetch += 1
    return need_fetch * WATCHMODE_HTTP_PER_AVAILABILITY_FETCH


def process_title_batch(
    titles,
    session,
    log,
    stage_label,
    wm_start,
    skip_rapidapi=False,
):
    """
    Warm TitleMeta/TitleGenres and availability for a deduped title dict.

    Each (tmdb_id, media_type) triggers at most one availability fetch per run.
    """
    progress = StageProgress(unique_titles=len(titles))

    for idx, ((tmdb_id, media_type), item) in enumerate(titles.items(), start=1):
        key = (tmdb_id, media_type)
        try:
            _refresh_title_metadata(item, media_type)

            if key in session.availability_fetched:
                progress.skipped_session += 1
                log(
                    '[warm_cache] [%s] [%d/%d] %s/%s - already fetched this run, skipped',
                    stage_label, idx, len(titles), media_type, tmdb_id,
                )
                continue

            if is_streaming_cache_fresh(tmdb_id, media_type):
                session.availability_fetched.add(key)
                progress.skipped_fresh += 1
                log(
                    '[warm_cache] [%s] [%d/%d] %s/%s - StreamingCache fresh, skipped',
                    stage_label, idx, len(titles), media_type, tmdb_id,
                )
                continue

            if _sync_from_fresh_content_cache(tmdb_id, media_type):
                session.availability_fetched.add(key)
                progress.skipped_fresh += 1
                log(
                    '[warm_cache] [%s] [%d/%d] %s/%s - synced from Content cache, skipped API',
                    stage_label, idx, len(titles), media_type, tmdb_id,
                )
                continue

            synced = _warm_streaming_availability(
                tmdb_id, media_type, skip_rapidapi=skip_rapidapi,
            )
            if synced:
                session.availability_fetched.add(key)
                progress.availability_fetches += 1
                log(
                    '[warm_cache] [%s] [%d/%d] %s/%s - availability synced (fetches=%d)',
                    stage_label, idx, len(titles), media_type, tmdb_id,
                    progress.availability_fetches,
                )
            else:
                progress.availability_failed += 1
                log(
                    '[warm_cache] [%s] [%d/%d] %s/%s - availability NOT synced '
                    '(no providers from RapidAPI/TMDB); will retry on next run',
                    stage_label, idx, len(titles), media_type, tmdb_id,
                )
        except Exception as exc:
            progress.errors += 1
            logger.warning(
                '[warm_cache] [%s] failed %s/%s: %s', stage_label, media_type, tmdb_id, exc,
            )

    progress.watchmode_http_calls = 0
    return progress


def warm_cache(log=logger.info, skip_rapidapi=False):
    """
    Two-stage cold-start warming:
      1) genre-balanced discover
      2) KR platform-targeted discover (TVING/Wavve/Watcha)
    Watchmode is disabled; RapidAPI + TMDB watch providers only.
    """
    session = WarmSession()
    log(
        '[warm_cache] starting%s',
        ' [RapidAPI skipped — TMDB providers only]' if skip_rapidapi else '',
    )

    # --- collect stage 1 ---
    stage1_titles = collect_genre_balanced_titles()
    stage1_keys = set(stage1_titles.keys())

    if len(stage1_titles) > UNIQUE_TITLE_BUDGET_WARN:
        logger.warning(
            '[warm_cache] BUDGET WARNING: stage1 deduped titles (%d) exceed ~450',
            len(stage1_titles),
        )

    # --- collect stage 2 (dedup against stage 1) ---
    stage2_titles = collect_platform_targeted_titles(stage1_keys)
    stage2_raw_max = len(KR_PLATFORMS_PROVIDER_ID) * 2 * PLATFORM_WARM_MAX_PAGES * 20

    log(
        '[warm_cache] pre-run estimate: stage1=%d titles (skip~%d), '
        'stage2=%d new titles (raw max %d)',
        len(stage1_titles),
        _count_skippable_titles(stage1_keys),
        len(stage2_titles),
        stage2_raw_max,
    )

    log('[warm_cache] === stage 1: genre-balanced warming ===')
    stage1_progress = process_title_batch(
        stage1_titles, session, log, 'stage1', 0,
        skip_rapidapi=skip_rapidapi,
    )

    log('[warm_cache] === stage 2: KR platform-targeted warming ===')
    stage2_progress = process_title_batch(
        stage2_titles, session, log, 'stage2', 0,
        skip_rapidapi=skip_rapidapi,
    )

    total_unique = len(stage1_titles) + len(stage2_titles)

    resynced = resync_streaming_cache_from_content()
    log('[warm_cache] backfilled StreamingCache from Content cache: %d titles', resynced)

    platform_counts = list(
        StreamingCache.objects
        .filter(available=True)
        .values('platform__name')
        .annotate(title_count=Count('tmdb_id', distinct=True))
        .order_by('-title_count')
    )

    return {
        'stage1': {
            'unique_titles': stage1_progress.unique_titles,
            'watchmode_http_calls': stage1_progress.watchmode_http_calls,
            'availability_fetches': stage1_progress.availability_fetches,
            'availability_failed': stage1_progress.availability_failed,
            'skipped_fresh': stage1_progress.skipped_fresh,
            'skipped_session': stage1_progress.skipped_session,
            'errors': stage1_progress.errors,
        },
        'stage2': {
            'unique_titles': stage2_progress.unique_titles,
            'watchmode_http_calls': stage2_progress.watchmode_http_calls,
            'availability_fetches': stage2_progress.availability_fetches,
            'availability_failed': stage2_progress.availability_failed,
            'skipped_fresh': stage2_progress.skipped_fresh,
            'skipped_session': stage2_progress.skipped_session,
            'errors': stage2_progress.errors,
        },
        'total_unique_titles': total_unique,
        'total_watchmode_http_calls': 0,
        'total_availability_fetches': (
            stage1_progress.availability_fetches + stage2_progress.availability_fetches
        ),
        'platform_counts': platform_counts,
    }


# Backward-compatible alias
def warm_genre_balanced_cache(log=logger.info):
    return warm_cache(log=log)
