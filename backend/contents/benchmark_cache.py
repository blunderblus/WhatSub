"""Cold-start cache warming and benchmark aggregation helpers."""
import logging
from datetime import date, timedelta

from django.utils import timezone

from subscriptions.models import Platform

from . import tmdb_client
from .title_display import poster_url_from_path, title_from_discover_item
from .models import (
    MediaType,
    PlatformGenreStats,
    StreamingCache,
    TitleGenres,
    TitleMeta,
)

logger = logging.getLogger(__name__)

STREAMING_CACHE_TTL = timedelta(hours=24)
UNIQUE_TITLE_BUDGET_WARN = 500


def _provider_platform_map():
    """Map TMDB watch-provider id → Platform."""
    return {
        p.tmdb_provider_id: p
        for p in Platform.objects.filter(tmdb_provider_id__isnull=False)
    }


def is_streaming_cache_fresh(tmdb_id, media_type):
    """True if any StreamingCache row for this title was checked within 24h."""
    latest = (
        StreamingCache.objects
        .filter(tmdb_id=tmdb_id, media_type=media_type)
        .order_by('-checked_at')
        .values_list('checked_at', flat=True)
        .first()
    )
    if not latest:
        return False
    return timezone.now() - latest < STREAMING_CACHE_TTL


def get_fresh_content(tmdb_id):
    """Return Content row if organic availability cache is still within 24h TTL."""
    from .models import Content

    content = Content.objects.filter(tmdb_id=tmdb_id).first()
    if not content or not content.sources_synced_at:
        return None
    if timezone.now() - content.sources_synced_at < STREAMING_CACHE_TTL:
        return content
    return None


def resync_streaming_cache_from_content():
    """Backfill StreamingCache from existing Content.sources_cache (no API calls)."""
    from .models import Content

    synced = 0
    for content in Content.objects.exclude(sources_cache=[]):
        media_type = content.content_type if content.content_type in ('movie', 'tv') else 'movie'
        sync_streaming_cache_from_providers(content.tmdb_id, media_type, content.sources_cache)
        synced += 1
    return synced


def sync_streaming_cache_from_tmdb(tmdb_id, media_type):
    """Fallback: fill StreamingCache from TMDB KR watch/providers (free, no RapidAPI)."""
    provider_map = _provider_platform_map()
    if not provider_map:
        return False
    try:
        provider_ids = tmdb_client.fetch_watch_providers(tmdb_id, media_type)
    except Exception as exc:
        logger.warning('TMDB watch/providers failed for %s/%s: %s', media_type, tmdb_id, exc)
        return False
    checked_at = timezone.now()
    synced = False
    for pid in provider_ids:
        platform = provider_map.get(pid)
        if not platform:
            continue
        StreamingCache.objects.update_or_create(
            tmdb_id=tmdb_id,
            media_type=media_type,
            platform=platform,
            defaults={'available': True, 'checked_at': checked_at},
        )
        synced = True
    return synced


def sync_streaming_cache_from_providers(tmdb_id, media_type, providers, checked_at=None):
    """Persist subscription availability into StreamingCache from provider dicts."""
    from subscriptions.platform_utils import resolve_official_platform

    checked_at = checked_at or timezone.now()
    for prov in providers:
        if prov.get('type') != 'subscription':
            continue
        platform = resolve_official_platform(name=prov.get('service') or '')
        if not platform:
            continue
        StreamingCache.objects.update_or_create(
            tmdb_id=tmdb_id,
            media_type=media_type,
            platform=platform,
            defaults={'available': True, 'checked_at': checked_at},
        )


def upsert_title_meta(item, media_type):
    title = title_from_discover_item(item)
    poster_url = poster_url_from_path(item.get('poster_path'))
    TitleMeta.objects.update_or_create(
        tmdb_id=item['id'],
        media_type=media_type,
        defaults={
            'title': title,
            'poster_url': poster_url,
            'vote_average': item.get('vote_average') or 0,
            'vote_count': item.get('vote_count') or 0,
            'popularity': item.get('popularity') or 0,
        },
    )


def sync_title_genres(tmdb_id, media_type, genre_ids):
    TitleGenres.objects.filter(tmdb_id=tmdb_id, media_type=media_type).delete()
    TitleGenres.objects.bulk_create([
        TitleGenres(tmdb_id=tmdb_id, media_type=media_type, genre_id=gid)
        for gid in genre_ids
        if gid
    ])


def _sync_streaming_cache(tmdb_id, media_type, provider_ids, provider_map, checked_at):
    """Upsert subscription availability rows for matched TMDB providers."""
    for pid in provider_ids:
        platform = provider_map.get(pid)
        if not platform:
            continue
        StreamingCache.objects.update_or_create(
            tmdb_id=tmdb_id,
            media_type=media_type,
            platform=platform,
            defaults={'available': True, 'checked_at': checked_at},
        )


def warm_title_from_discover(item, media_type, provider_map, checked_at):
    """Persist TitleMeta, TitleGenres, and StreamingCache for one discover result."""
    tmdb_id = item['id']
    upsert_title_meta(item, media_type)
    sync_title_genres(tmdb_id, media_type, item.get('genre_ids') or [])

    try:
        provider_ids = tmdb_client.fetch_watch_providers(tmdb_id, media_type)
    except Exception as exc:
        logger.warning('Watch providers failed for %s/%s: %s', media_type, tmdb_id, exc)
        provider_ids = []

    _sync_streaming_cache(tmdb_id, media_type, provider_ids, provider_map, checked_at)
    return tmdb_id


def warm_popular_titles(pages=5, media_types=None):
    """
    Cold-start: fetch TMDB popular movie/TV titles and warm benchmark caches.

    Returns summary dict with counts per step.
    """
    media_types = media_types or [MediaType.MOVIE, MediaType.TV]
    provider_map = _provider_platform_map()
    if not provider_map:
        raise RuntimeError(
            'No Platform rows with tmdb_provider_id — load platform_seed fixture first.',
        )

    checked_at = timezone.now()
    stats = {
        'titles_processed': 0,
        'meta_upserted': 0,
        'genres_synced': 0,
        'streaming_rows': 0,
        'errors': 0,
    }

    for media_type in media_types:
        for page in range(1, pages + 1):
            try:
                data = tmdb_client.discover_popular(media_type, page=page)
            except Exception as exc:
                logger.error('Discover failed %s page %s: %s', media_type, page, exc)
                stats['errors'] += 1
                continue

            for item in data.get('results') or []:
                try:
                    warm_title_from_discover(item, media_type, provider_map, checked_at)
                    stats['titles_processed'] += 1
                except Exception as exc:
                    logger.warning('Warm failed for %s/%s: %s', media_type, item.get('id'), exc)
                    stats['errors'] += 1

    stats['meta_upserted'] = TitleMeta.objects.count()
    stats['genres_synced'] = TitleGenres.objects.count()
    stats['streaming_rows'] = StreamingCache.objects.filter(available=True).count()
    return stats


def aggregate_platform_genre_stats(snapshot_date=None):
    """
    Aggregate StreamingCache + TitleGenres into PlatformGenreStats.

    Counts available titles per (platform, genre_id) for the given snapshot date.
    """
    snapshot_date = snapshot_date or timezone.localdate()

    genre_lookup = {}
    for tg in TitleGenres.objects.values('tmdb_id', 'media_type', 'genre_id'):
        key = (tg['tmdb_id'], tg['media_type'])
        genre_lookup.setdefault(key, []).append(tg['genre_id'])

    counts = {}
    for row in StreamingCache.objects.filter(available=True).values(
        'platform_id', 'tmdb_id', 'media_type',
    ):
        for genre_id in genre_lookup.get((row['tmdb_id'], row['media_type']), []):
            key = (row['platform_id'], genre_id)
            counts[key] = counts.get(key, 0) + 1

    PlatformGenreStats.objects.filter(snapshot_date=snapshot_date).delete()
    PlatformGenreStats.objects.bulk_create([
        PlatformGenreStats(
            platform_id=platform_id,
            genre_id=genre_id,
            title_count=title_count,
            snapshot_date=snapshot_date,
        )
        for (platform_id, genre_id), title_count in counts.items()
    ])

    return {
        'snapshot_date': snapshot_date.isoformat(),
        'platform_genre_rows': len(counts),
        'total_titles_in_cache': StreamingCache.objects.filter(available=True).values(
            'tmdb_id', 'media_type',
        ).distinct().count(),
    }


def run_cold_start(pages=5, snapshot_date=None):
    """Full cold-start pipeline: warm caches then aggregate genre stats."""
    warm_stats = warm_popular_titles(pages=pages)
    agg_stats = aggregate_platform_genre_stats(snapshot_date=snapshot_date or date.today())
    return {'warm': warm_stats, 'aggregate': agg_stats}
