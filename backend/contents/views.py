from datetime import timedelta
import logging
import time

import requests
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from subscriptions.models import Platform
from . import watchmode as wm
from .image_urls import find_nested_image_url, tmdb_image_url
from .models import Content, ContentPlatform, ContentReaction, StreamingCache, TitleGenres, TitleMeta, WatchmodeUsage
from .streaming_provider_display import (
    CONTENT_PLATFORM_SOURCE_TYPES,
    PROVIDER_PRIORITY,
    decorate_providers,
    normalized_service,
    provider_key,
    provider_type_label,
    sort_providers,
)
from .title_display import get_title_display_map
from .tmdb_response_cache import TMDB_DISCOVER_CACHE_TTL, TMDB_GENRE_CACHE_TTL, get_or_fetch_tmdb_json

logger = logging.getLogger(__name__)

SOURCES_CACHE_TTL = timedelta(hours=24)
RAPIDAPI_MIN_INTERVAL_SEC = 0.35
RAPIDAPI_429_MAX_RETRIES = 4
_last_rapidapi_request_at = 0.0
DISCOVER_PAGE_SIZE = 20

# TMDB discover returns empty for these KR providers — use StreamingCache instead.
_KR_UNRELIABLE_TMDB_PROVIDER_IDS = {200, 356, 97}  # TVING, Wavve, Watcha

# TMDB genre APIs
def tmdb_genres(request):
    return _tmdb_genres('movie')


def tmdb_show_genres(request):
    return _tmdb_genres('tv')


def _tmdb_genres(media_type):
    url = f'https://api.themoviedb.org/3/genre/{media_type}/list'
    params = {
        'language': 'ko-KR',
    }

    try:
        data = get_or_fetch_tmdb_json(
            'genres',
            url,
            params,
            lambda: _tmdb_get(url, params),
            TMDB_GENRE_CACHE_TTL,
        )
        return JsonResponse({'genres': data.get('genres', [])}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def tmdb_movie_list(request):
    return _tmdb_discover(request, 'movie')


def tmdb_show_list(request):
    return _tmdb_discover(request, 'tv')


def _parse_platform_ids(request):
    ids = []
    for raw in request.GET.getlist('platform_id'):
        text = str(raw).strip()
        if text.isdigit():
            ids.append(int(text))
    extra = request.GET.get('platform_ids', '')
    if extra:
        for raw in extra.split(','):
            text = str(raw).strip()
            if text.isdigit():
                ids.append(int(text))
    return list(dict.fromkeys(ids))


def _platform_prefers_streaming_cache(platform):
    if not platform.tmdb_provider_id:
        return True
    if platform.tmdb_provider_id in _KR_UNRELIABLE_TMDB_PROVIDER_IDS:
        return True
    if platform.name in {'TVING', 'Wavve', 'Watcha', 'Coupang Play', 'SPOTV'}:
        return True
    return False


def _tmdb_discover(request, media_type):
    genre_id = request.GET.get('genre')
    platform_ids = _parse_platform_ids(request)
    page = request.GET.get('page', 1)
    live = request.GET.get('live') == '1'

    if platform_ids:
        platforms = list(Platform.objects.filter(pk__in=platform_ids))
        if not platforms:
            return JsonResponse({'page': 1, 'total_pages': 1, 'results': []}, json_dumps_params={'ensure_ascii': False})

        provider_ids = [p.tmdb_provider_id for p in platforms if p.tmdb_provider_id]
        use_cache = any(_platform_prefers_streaming_cache(p) for p in platforms)
        if live and provider_ids:
            use_cache = False
        if not use_cache:
            cache_count = StreamingCache.objects.filter(
                platform_id__in=platform_ids, media_type=media_type, available=True,
            ).count()
            use_cache = cache_count > 0 and not live

        if use_cache:
            return _streaming_cache_list(request, media_type, platform_ids, genre_id=genre_id)

        if not provider_ids:
            return _streaming_cache_list(request, media_type, platform_ids, genre_id=genre_id)

        params = {
            'language': 'ko-KR',
            'include_adult': 'false',
            'sort_by': 'popularity.desc',
            'watch_region': 'KR',
            'with_watch_providers': '|'.join(str(pid) for pid in provider_ids),
        }
        if genre_id:
            params['with_genres'] = genre_id
        try:
            data = _tmdb_discover_page(media_type, params, page)
            if not data.get('results') and len(platform_ids) == 1:
                return _streaming_cache_list(request, media_type, platform_ids, genre_id=genre_id)
            return _filled_discover_response(media_type, params, page, first_page_data=data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    params = {
        'language': 'ko-KR',
        'include_adult': 'false',
        'sort_by': 'popularity.desc',
        'watch_region': 'KR',
    }

    if genre_id:
        params['with_genres'] = genre_id

    try:
        return _filled_discover_response(media_type, params, page)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _filled_discover_response(media_type, params, requested_page, first_page_data=None):
    page = _positive_int(requested_page, default=1)
    target_count = page * DISCOVER_PAGE_SIZE
    visible_items = []
    source_page = 1
    total_pages = 1

    while len(visible_items) < target_count and source_page <= total_pages:
        data = first_page_data if source_page == page and first_page_data is not None else _tmdb_discover_page(
            media_type, params, source_page,
        )
        total_pages = min(_positive_int(data.get('total_pages'), default=1), 500)
        visible_items.extend([
            item
            for item in data.get('results', [])
            if _has_korean_catalog_value(item)
        ])
        source_page += 1

    start = (page - 1) * DISCOVER_PAGE_SIZE
    end = page * DISCOVER_PAGE_SIZE
    return _format_discover_response({
        'page': page,
        'total_pages': total_pages,
        'results': visible_items[start:end],
    }, media_type)


def _tmdb_discover_page(media_type, params, page):
    url = f'https://api.themoviedb.org/3/discover/{media_type}'
    request_params = {
        **params,
        'page': page,
    }
    return get_or_fetch_tmdb_json(
        'discover',
        url,
        request_params,
        lambda: _tmdb_get(url, request_params),
        TMDB_DISCOVER_CACHE_TTL,
    )


def _format_discover_response(data, media_type):
    movies = []
    for item in data.get('results', []):
        movies.append({
            'tmdb_id': item.get('id'),
            'media_type': media_type,
            'title': item.get('title') or item.get('name') or item.get('original_title') or item.get('original_name'),
            'overview': item.get('overview') or '줄거리 정보가 아직 없습니다.',
            'release_date': item.get('release_date') or item.get('first_air_date') or '',
            'rating': item.get('vote_average') or 0,
            'popularity': item.get('popularity') or 0,
            'poster_url': (
                f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}"
                if item.get('poster_path')
                else None
            ),
        })

    return JsonResponse({
        'page': data.get('page', 1),
        'total_pages': data.get('total_pages', 1),
        'results': movies,
    }, json_dumps_params={'ensure_ascii': False})


def _has_korean_catalog_value(item):
    return _has_korean_title(item) or bool((item.get('overview') or '').strip())


def _has_display_catalog_value(item):
    return _contains_hangul(item.get('title') or '') or bool((item.get('overview') or '').strip())


def _has_korean_title(item):
    title = item.get('title') or item.get('name') or ''
    original_title = item.get('original_title') or item.get('original_name') or ''
    if not title.strip():
        return False
    if _contains_hangul(title):
        return True
    if not original_title.strip():
        return False
    return title.strip().casefold() != original_title.strip().casefold()


def _contains_hangul(value):
    return any('\uac00' <= char <= '\ud7a3' for char in value)


def _positive_int(value, default=1):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def _streaming_cache_list(request, media_type, platform_ids, genre_id=None):
    """Paginated title list from StreamingCache (supports multi-platform OR)."""
    if not isinstance(platform_ids, (list, tuple)):
        platform_ids = [platform_ids]

    page = int(request.GET.get('page', 1))
    per_page = 20
    qs = StreamingCache.objects.filter(
        platform_id__in=platform_ids, media_type=media_type, available=True,
    )
    keys = list(qs.values_list('tmdb_id', 'media_type').distinct())

    if genre_id:
        genre_keys = set(
            TitleGenres.objects.filter(
                genre_id=genre_id, media_type=media_type,
            ).values_list('tmdb_id', 'media_type')
        )
        keys = [k for k in keys if k in genre_keys]

    popularity_by_key = {
        (meta.tmdb_id, meta.media_type): meta.popularity or 0
        for meta in TitleMeta.objects.filter(
            tmdb_id__in=[tmdb_id for tmdb_id, _ in keys],
            media_type=media_type,
        )
    }
    keys.sort(key=lambda row: (popularity_by_key.get(row, 0), row[0]), reverse=True)
    page = _positive_int(page, default=1)
    visible_results = []
    target_count = page * per_page
    source_offset = 0

    while len(visible_results) < target_count and source_offset < len(keys):
        chunk = keys[source_offset:source_offset + per_page]
        display_map = get_title_display_map(chunk, max_tmdb_fetches=per_page)
        meta_map = {
            (meta.tmdb_id, meta.media_type): meta
            for meta in TitleMeta.objects.filter(
                tmdb_id__in=[tmdb_id for tmdb_id, _ in chunk],
                media_type=media_type,
            )
        }

        for tmdb_id, mt in chunk:
            info = display_map.get((tmdb_id, mt), {})
            meta = meta_map.get((tmdb_id, mt))
            title = info.get('title') or f'작품 #{tmdb_id}'
            item = {
                'tmdb_id': tmdb_id,
                'media_type': mt,
                'title': title,
                'overview': '',
                'release_date': '',
                'rating': meta.vote_average if meta else 0,
                'popularity': meta.popularity if meta else 0,
                'poster_url': info.get('poster_url') or '',
            }
            if _has_display_catalog_value(item):
                visible_results.append(item)
        source_offset += per_page

    start = (page - 1) * per_page
    end = page * per_page
    results = visible_results[start:end]

    return JsonResponse({
        'page': page,
        'total_pages': max((len(keys) + per_page - 1) // per_page, 1),
        'results': results,
        'source': 'streaming_cache',
    }, json_dumps_params={'ensure_ascii': False})


def streaming_platforms_filter(request):
    """Platforms with cached titles for content list filter."""
    qs = StreamingCache.objects.filter(available=True)
    media_type = (request.GET.get('media_type') or '').strip().lower()
    if media_type in ('movie', 'movies'):
        qs = qs.filter(media_type='movie')
    elif media_type in ('tv', 'show', 'shows', 'series'):
        qs = qs.filter(media_type='tv')

    rows = (
        qs
        .values('platform_id', 'platform__name')
        .annotate(title_count=Count('tmdb_id', distinct=True))
        .order_by('-title_count')
    )
    from .benchmark_constants import platform_icon
    return JsonResponse({
        'platforms': [
            {
                'platform_id': r['platform_id'],
                'name': r['platform__name'],
                'title_count': r['title_count'],
                'icon_url': platform_icon(r['platform__name']),
            }
            for r in rows
        ],
    }, json_dumps_params={'ensure_ascii': False})


def tmdb_movie_detail(request, tmdb_id):
    return _tmdb_content_detail(request, tmdb_id, 'movie')


def tmdb_show_detail(request, tmdb_id):
    return _tmdb_content_detail(request, tmdb_id, 'tv')


def _tmdb_content_detail(request, tmdb_id, media_type):
    try:
        detail = _tmdb_get(f'https://api.themoviedb.org/3/{media_type}/{tmdb_id}', {
            'append_to_response': 'credits',
            'language': 'ko-KR',
        })

        cast = []
        for person in detail.get('credits', {}).get('cast', [])[:12]:
            cast.append({
                'name': person.get('name'),
                'character': person.get('character') or '',
                'profile_url': tmdb_image_url(person.get('profile_path'), 'w185'),
            })

        runtime = detail.get('runtime') or 0
        if not runtime and detail.get('episode_run_time'):
            runtime = detail.get('episode_run_time')[0]

        movie = {
            'tmdb_id': detail.get('id'),
            'title': detail.get('title') or detail.get('name') or detail.get('original_title') or detail.get('original_name'),
            'original_title': detail.get('original_title') or detail.get('original_name') or '',
            'overview': detail.get('overview') or '줄거리 정보가 아직 없습니다.',
            'release_date': detail.get('release_date') or detail.get('first_air_date') or '',
            'runtime': runtime,
            'rating': detail.get('vote_average') or 0,
            'genres': detail.get('genres', []),
            'poster_url': tmdb_image_url(detail.get('poster_path'), 'w500'),
            'backdrop_url': tmdb_image_url(detail.get('backdrop_path'), 'w1280'),
            'cast': cast,
        }

        payload = {
            'movie': movie,
            'providers': get_streaming_providers(
                tmdb_id, media_type,
                allow_watchmode=True,
                allow_rapidapi_fallback=True,
                skip_rapidapi=True,
            ),
            'reactions': _reaction_summary_for_tmdb(tmdb_id, request.user),
        }
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code if err.response is not None else 500
        return JsonResponse({'error': f'TMDB API HTTP 오류: {err}'}, status=status_code)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def _tmdb_get(url, params=None):
    request_params = {
        'api_key': settings.TMDB_API_KEY,
        **(params or {}),
    }
    response = requests.get(url, params=request_params)
    response.raise_for_status()
    return response.json()


def _should_augment_watchmode(providers):
    """True when KR locals are missing or present without a deep link."""
    present = {(p.get('service') or '').lower() for p in providers}
    if not wm.KR_LOCAL_SERVICES.intersection(present):
        return True
    for svc in wm.KR_LOCAL_SERVICES:
        if svc not in present:
            continue
        entries = [p for p in providers if (p.get('service') or '').lower() == svc]
        if entries and not any(p.get('link') for p in entries):
            return True
    return False


def _collapse_same_platform(providers):
    """Same platform: drop link-less duplicates when a linked entry exists."""
    by_service = {}
    for prov in providers:
        svc = normalized_service(prov)
        by_service.setdefault(svc, []).append(dict(prov))

    collapsed = []
    for group in by_service.values():
        linked = [p for p in group if (p.get('link') or '').strip()]
        pool = linked if linked else group
        by_type = {}
        for prov in pool:
            ptype = prov.get('type') or 'subscription'
            current = by_type.get(ptype)
            if not current or ((prov.get('link') or '').strip() and not (current.get('link') or '').strip()):
                by_type[ptype] = prov
        collapsed.extend(by_type.values())
    return collapsed


def _dedupe_providers(providers):
    providers = _collapse_same_platform(providers)
    return sort_providers(providers)


def _preserve_deeplinks(new_providers, old_providers):
    """Keep cached deep links when a refresh drops them."""
    old_by_key = {}
    for prov in old_providers or []:
        if not (prov.get('link') or '').strip():
            continue
        old_by_key[provider_key(prov)] = prov

    if not old_by_key:
        return new_providers

    merged = []
    seen_keys = set()
    for prov in new_providers:
        prov = dict(prov)
        key = provider_key(prov)
        seen_keys.add(key)
        if not (prov.get('link') or '').strip() and key in old_by_key:
            old = old_by_key[key]
            prov['link'] = old['link']
            prov['source'] = old.get('source') or prov.get('source')
            if prov.get('price') is None and old.get('price') is not None:
                prov['price'] = old['price']
        merged.append(prov)

    new_keys = {provider_key(p) for p in merged}
    for key, old in old_by_key.items():
        if key not in new_keys:
            merged.append(dict(old))
    return merged


def _enrich_provider_links(content, providers):
    """Fill missing links from ContentPlatform rows (survives TMDB-only refresh)."""
    from subscriptions.platform_utils import resolve_official_platform

    cp_links = {}
    for row in content.platform_sources.filter(is_available=True).exclude(deeplink_url='').select_related('platform'):
        cp_links[row.platform.name.lower()] = row.deeplink_url

    enriched = []
    for prov in providers:
        prov = dict(prov)
        if not (prov.get('link') or '').strip():
            svc = normalized_service(prov)
            platform = resolve_official_platform(name=prov.get('service') or prov.get('display_name') or '')
            if platform and platform.name.lower() in cp_links:
                prov['link'] = cp_links[platform.name.lower()]
            elif svc in cp_links:
                prov['link'] = cp_links[svc]
        enriched.append(prov)
    return enriched


def _providers_missing_links(providers):
    return any(not (p.get('link') or '').strip() for p in providers)


def _merge_providers_prefer_links(primary, secondary):
    by_key = {provider_key(p): dict(p) for p in primary}
    for prov in secondary:
        key = provider_key(prov)
        if key not in by_key:
            by_key[key] = dict(prov)
            continue
        existing = by_key[key]
        if (prov.get('link') or '').strip() and not (existing.get('link') or '').strip():
            existing['link'] = prov['link']
            existing['source'] = prov.get('source') or existing.get('source')
        if not existing.get('icon_url') and prov.get('icon_url'):
            existing['icon_url'] = prov['icon_url']
        if existing.get('price') is None and prov.get('price') is not None:
            existing['price'] = prov['price']
    return sort_providers(by_key.values())


def _try_rapidapi_link_fallback(content, tmdb_id, media_type, providers):
    if not getattr(settings, 'RAPIDAPI_KEY', ''):
        return providers
    try:
        rapid = _parse_streaming_providers(_fetch_streaming_availability(tmdb_id, media_type))
    except Exception as exc:  # noqa: BLE001
        logger.warning('RapidAPI link fallback failed for %s/%s: %s', media_type, tmdb_id, exc)
        return providers
    if not rapid:
        return providers
    merged = _merge_providers_prefer_links(providers, rapid)
    if merged != providers:
        merged = _finalize_providers(content, merged)
        content.sources_cache = merged
        content.sources_synced_at = timezone.now()
        content.save(update_fields=['sources_cache', 'sources_synced_at'])
        _sync_content_platforms(content, merged)
    return merged


def _finalize_providers(content, providers):
    providers = _dedupe_providers(providers)
    providers = _enrich_provider_links(content, providers)
    return providers


def _merge_providers(primary, secondary):
    """Merge two provider lists, de-duplicating by (service name, type)."""
    return _merge_providers_prefer_links(primary, secondary)


def _sync_content_platforms(content, providers):
    """Persist availability rows for providers that map to a known Platform."""
    from subscriptions.platform_utils import resolve_official_platform

    for prov in providers:
        platform = resolve_official_platform(name=prov.get('service') or '')
        source_type = CONTENT_PLATFORM_SOURCE_TYPES.get(prov.get('type'))
        if not platform or not source_type:
            continue
        defaults = {
            'price': prov.get('price'),
            'is_available': True,
        }
        if prov.get('link'):
            defaults['deeplink_url'] = prov['link']
        ContentPlatform.objects.update_or_create(
            content=content, platform=platform, source_type=source_type,
            defaults=defaults,
        )


def _augment_with_watchmode(content, tmdb_id, media_type, providers):
    """Fill KR availability gaps using Watchmode. Returns (providers, api_calls)."""
    calls = 0
    watchmode_id = content.watchmode_id
    if not watchmode_id:
        watchmode_id = wm.resolve_watchmode_id(tmdb_id, media_type)
        calls += 1
        if watchmode_id:
            content.watchmode_id = watchmode_id
    if watchmode_id:
        wm_providers = wm.parse_sources(wm.fetch_sources(watchmode_id, 'KR'))
        calls += 1
        providers = _merge_providers(providers, wm_providers)
    return providers, calls


def get_streaming_providers(
    tmdb_id, media_type, allow_watchmode=False, force_refresh=False,
    skip_rapidapi=True, allow_rapidapi_fallback=False,
):
    """
    Resolve per-title KR streaming availability with a 24h DB cache.

    TMDB watch/providers is the default source (fast). Watchmode supplements
    KR locals (TVING / Wavve / Watcha) with title deep links on detail pages.
    """
    content, _ = Content.objects.get_or_create(
        tmdb_id=tmdb_id,
        defaults={'title': '', 'content_type': media_type},
    )
    is_fresh = (
        not force_refresh
        and content.sources_synced_at
        and timezone.now() - content.sources_synced_at < SOURCES_CACHE_TTL
    )

    if is_fresh:
        providers = _finalize_providers(content, content.sources_cache or [])
        return decorate_providers(providers)

    old_providers = list(content.sources_cache or [])
    rapidapi_failed = False
    if skip_rapidapi:
        providers = _providers_from_tmdb_watch(tmdb_id, media_type)
    else:
        try:
            providers = _parse_streaming_providers(
                _fetch_streaming_availability(tmdb_id, media_type)
            )
        except Exception as exc:  # noqa: BLE001 - never let availability break the page
            rapidapi_failed = True
            logger.warning(
                'RapidAPI availability failed for %s/%s: %s', media_type, tmdb_id, exc,
            )
            providers = _providers_from_tmdb_watch(tmdb_id, media_type)

    providers = _preserve_deeplinks(providers, old_providers)

    if (
        allow_watchmode
        and wm.is_configured()
        and WatchmodeUsage.can_call()
        and _should_augment_watchmode(providers)
    ):
        providers, calls = _augment_with_watchmode(content, tmdb_id, media_type, providers)
        if calls:
            WatchmodeUsage.increment(calls)

    providers = _finalize_providers(content, providers)

    should_persist = bool(providers) or skip_rapidapi or not rapidapi_failed
    if should_persist:
        content.sources_cache = providers
        content.sources_synced_at = timezone.now()
        content.save(update_fields=['sources_cache', 'sources_synced_at', 'watchmode_id'])
        _sync_content_platforms(content, providers)

    if allow_rapidapi_fallback and _providers_missing_links(providers):
        providers = _try_rapidapi_link_fallback(content, tmdb_id, media_type, providers)

    return decorate_providers(providers)


def _providers_from_tmdb_watch(tmdb_id, media_type):
    """Build provider dicts from TMDB watch/providers (KR) — no RapidAPI."""
    try:
        data = _tmdb_get(
            f'https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers',
            {},
        )
    except Exception as exc:
        logger.warning('TMDB watch/providers failed for %s/%s: %s', media_type, tmdb_id, exc)
        return []

    region = (data.get('results') or {}).get('KR') or {}
    type_map = (
        ('flatrate', 'subscription', '구독'),
        ('free', 'free', '무료'),
        ('ads', 'ads', '광고 포함'),
        ('rent', 'rent', '대여'),
        ('buy', 'buy', '구매'),
    )
    providers = []
    seen = set()
    for key, ptype, label in type_map:
        for item in region.get(key) or []:
            name = item.get('provider_name') or ''
            dedupe = (name.lower(), ptype)
            if not name or dedupe in seen:
                continue
            seen.add(dedupe)
            logo = item.get('logo_path')
            providers.append({
                'service': name,
                'display_name': name,
                'type': ptype,
                'type_label': label,
                'icon_url': tmdb_image_url(logo, 'w45') if logo else None,
                'source': 'tmdb',
            })
    return sorted(providers, key=lambda x: PROVIDER_PRIORITY.get(x.get('type'), 99))


def _fetch_streaming_availability(tmdb_id, media_type):
    global _last_rapidapi_request_at

    rapidapi_key = getattr(settings, 'RAPIDAPI_KEY', '')
    formatted_id = f"{media_type}/{tmdb_id}"
    url = f"https://streaming-availability.p.rapidapi.com/shows/{formatted_id}"
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
    }

    elapsed = time.monotonic() - _last_rapidapi_request_at
    if elapsed < RAPIDAPI_MIN_INTERVAL_SEC:
        time.sleep(RAPIDAPI_MIN_INTERVAL_SEC - elapsed)

    last_exc = None
    for attempt in range(RAPIDAPI_429_MAX_RETRIES):
        _last_rapidapi_request_at = time.monotonic()
        response = requests.get(url, headers=headers, params={"country": "kr"}, timeout=30)
        if response.status_code == 404:
            return {}
        if response.status_code == 429:
            last_exc = requests.HTTPError(
                f'429 Too Many Requests for {formatted_id}', response=response,
            )
            if attempt < RAPIDAPI_429_MAX_RETRIES - 1:
                backoff = 2 ** (attempt + 1)
                logger.warning(
                    'RapidAPI 429 for %s — retry %d/%d in %ds',
                    formatted_id, attempt + 1, RAPIDAPI_429_MAX_RETRIES - 1, backoff,
                )
                time.sleep(backoff)
                continue
            response.raise_for_status()
        response.raise_for_status()
        return response.json()

    if last_exc:
        raise last_exc
    return {}


def _parse_streaming_providers(data):
    providers = []
    seen = set()
    addon_added = False
    if isinstance(data, dict) and 'streamingOptions' in data:
        kr_options = data.get('streamingOptions', {}).get('kr', [])
        for option in kr_options:
            service = option.get('service', {})
            addon = option.get('addon') or {}
            provider_type = option.get('type')
            if provider_type == 'addon':
                if addon_added:
                    continue
                addon_added = True

            service_id = service.get('id') or service.get('name')
            addon_id = addon.get('id') or addon.get('name') or ''
            dedupe_key = (service_id, provider_type, addon_id)

            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            service_name = service.get('name')
            addon_name = addon.get('name')

            providers.append({
                'service': service_name,
                'service_id': service.get('id'),
                'addon': addon_name,
                'display_name': service_name,
                'type': provider_type,
                'type_label': provider_type_label(provider_type),
                'expires_on': option.get('expiresOn'),
                'link': option.get('videoLink') or option.get('link'),
                'icon_url': find_nested_image_url(service),
            })

    return sorted(providers, key=lambda provider: PROVIDER_PRIORITY.get(provider.get('type'), 99))


# TMDB movie/show search API
def tmdb_search(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'results': []})

    url = 'https://api.themoviedb.org/3/search/multi'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'query': query,
        'language': 'ko-KR',
        'include_adult': 'false',
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        results = []

        for item in data.get('results', []):
            if item.get('media_type') not in ['movie', 'tv']:
                continue

            results.append({
                'tmdb_id': item.get('id'),
                'title': item.get('title') or item.get('name'),
                'media_type': item.get('media_type'),
                'release_date': item.get('release_date') or item.get('first_air_date'),
                'poster_url': (f"https://image.tmdb.org/t/p/w200{item.get('poster_path')}" if item.get('poster_path') else None),
            })

        return JsonResponse({'results': results}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Streaming availability API
def api_streaming_info(request):
    tmdb_id = request.GET.get('tmdb_id')
    # media_type is either "movie" or "tv" from TMDB.
    media_type = request.GET.get('media_type')
    
    if not tmdb_id or not media_type:
        return JsonResponse({'error': '필수 파라미터가 없습니다.'}, status=400)

    try:
        # List-grid hover: RapidAPI only (cheap). Watchmode enrichment is
        # reserved for the detail page to protect the monthly free-tier budget.
        payload = {
            'providers': get_streaming_providers(tmdb_id, media_type, allow_watchmode=False),
        }
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': f"서버 오류: {str(e)}"}, status=500)


def _reaction_summary_for_tmdb(tmdb_id, user):
    content = Content.objects.filter(tmdb_id=tmdb_id).first()
    if not content:
        return {'like_count': 0, 'dislike_count': 0, 'my_reaction': None}
    return _reaction_summary(content, user)


def _reaction_summary(content, user):
    counts = dict(
        content.reactions.values('reaction').annotate(total=Count('id')).values_list('reaction', 'total')
    )
    my_reaction = None
    if getattr(user, 'is_authenticated', False):
        my_reaction = (
            ContentReaction.objects
            .filter(content=content, user=user)
            .values_list('reaction', flat=True)
            .first()
        )
    return {
        'like_count': counts.get(ContentReaction.Reaction.LIKE, 0),
        'dislike_count': counts.get(ContentReaction.Reaction.DISLIKE, 0),
        'my_reaction': my_reaction,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def content_reaction(request, tmdb_id):
    media_type = request.data.get('media_type') or ''
    reaction = request.data.get('reaction')
    if reaction not in [ContentReaction.Reaction.LIKE, ContentReaction.Reaction.DISLIKE, None, '']:
        return JsonResponse({'error': '올바른 반응 값이 아닙니다.'}, status=400)

    content, _ = Content.objects.get_or_create(
        tmdb_id=tmdb_id,
        defaults={'title': '', 'content_type': media_type},
    )
    title_hint = (request.data.get('title') or '').strip()
    poster_hint = (request.data.get('poster_url') or '').strip()
    if title_hint or poster_hint:
        from .title_display import upsert_title_display
        upsert_title_display(tmdb_id, media_type, title_hint, poster_hint)
    elif media_type and not (content.korean_title or content.title):
        from . import tmdb_client
        from .title_display import upsert_title_display
        try:
            brief = tmdb_client.fetch_title_brief(tmdb_id, media_type)
            upsert_title_display(tmdb_id, media_type, brief.get('title', ''), brief.get('poster_url', ''))
            content.refresh_from_db()
        except Exception:
            pass

    existing = ContentReaction.objects.filter(content=content, user=request.user).first()
    if not reaction or (existing and existing.reaction == reaction):
        if existing:
            existing.delete()
    elif existing:
        existing.reaction = reaction
        existing.save(update_fields=['reaction', 'updated_at'])
    else:
        ContentReaction.objects.create(content=content, user=request.user, reaction=reaction)

    return JsonResponse(_reaction_summary(content, request.user), json_dumps_params={'ensure_ascii': False})
