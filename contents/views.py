from datetime import timedelta

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from subscriptions.models import Platform
from . import watchmode as wm
from .models import Content, ContentPlatform, WatchmodeUsage

SOURCES_CACHE_TTL = timedelta(hours=24)
_PROVIDER_PRIORITY = {'subscription': 0, 'free': 1, 'ads': 2, 'rent': 3, 'buy': 4, 'addon': 5}
_TYPE_TO_SOURCE = {'subscription': 'sub', 'free': 'free', 'rent': 'rent', 'buy': 'buy'}

# Maps normalized provider names (from RapidAPI / Watchmode) to a canonical
# display name and a local icon file under MEDIA_ROOT (subscriptions/media).
_PLATFORM_ICONS = {
    'netflix': ('Netflix', 'Netflix_icon.png'),
    'disney+': ('Disney+', 'DisneyPlus_icon.png'),
    'disneyplus': ('Disney+', 'DisneyPlus_icon.png'),
    'disney plus': ('Disney+', 'DisneyPlus_icon.png'),
    'apple tv+': ('Apple TV+', 'AppleTV_icon.png'),
    'apple tv plus': ('Apple TV+', 'AppleTV_icon.png'),
    'apple tv': ('Apple TV+', 'AppleTV_icon.png'),
    'appletv': ('Apple TV+', 'AppleTV_icon.png'),
    'amazon prime video': ('Amazon Prime Video', 'AmazonPrimeVideo_icon.png'),
    'prime video': ('Amazon Prime Video', 'AmazonPrimeVideo_icon.png'),
    'amazon video': ('Amazon Prime Video', 'AmazonPrimeVideo_icon.png'),
    'amazon': ('Amazon Prime Video', 'AmazonPrimeVideo_icon.png'),
    'coupang play': ('Coupang Play', 'CoupangPlay_icon.png'),
    'coupangplay': ('Coupang Play', 'CoupangPlay_icon.png'),
    'tving': ('TVING', 'TVING_icon.png'),
    'wavve': ('Wavve', 'Wavve_icon.png'),
    'watcha': ('Watcha', 'Watcha_icon.webp'),
    'spotv': ('SPOTV', 'SpotvNow_icon.png'),
    'spotv now': ('SPOTV', 'SpotvNow_icon.png'),
    'spotvnow': ('SPOTV', 'SpotvNow_icon.png'),
}

# 1. 검색 화면 렌더링 뷰
def search_page(request):
    return render(request, 'contents/search_page.html')


def movie_list_page(request):
    return render(request, 'contents/movie_list.html', {
        'media_type': 'movie',
        'content_label': '영화',
        'content_label_en': 'Movies',
        'list_api_url': '/contents/movie_list/',
        'genres_api_url': '/contents/genres/',
        'detail_base_url': '/contents/movies/',
    })


def movie_detail_page(request, tmdb_id):
    return render(request, 'contents/movie_detail.html', {
        'tmdb_id': tmdb_id,
        'media_type': 'movie',
        'content_label': '영화',
        'content_label_en': 'Movies',
        'detail_api_url': f'/contents/movie_detail/{tmdb_id}/',
        'list_url': '/contents/movies/',
    })


def show_list_page(request):
    return render(request, 'contents/movie_list.html', {
        'media_type': 'tv',
        'content_label': '드라마',
        'content_label_en': 'Shows',
        'list_api_url': '/contents/show_list/',
        'genres_api_url': '/contents/show_genres/',
        'detail_base_url': '/contents/shows/',
    })


def show_detail_page(request, tmdb_id):
    return render(request, 'contents/movie_detail.html', {
        'tmdb_id': tmdb_id,
        'media_type': 'tv',
        'content_label': '드라마',
        'content_label_en': 'Shows',
        'detail_api_url': f'/contents/show_detail/{tmdb_id}/',
        'list_url': '/contents/shows/',
    })


def tmdb_genres(request):
    return _tmdb_genres('movie')


def tmdb_show_genres(request):
    return _tmdb_genres('tv')


def _tmdb_genres(media_type):
    url = f'https://api.themoviedb.org/3/genre/{media_type}/list'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'ko-KR',
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return JsonResponse({'genres': data.get('genres', [])}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def tmdb_movie_list(request):
    return _tmdb_discover(request, 'movie')


def tmdb_show_list(request):
    return _tmdb_discover(request, 'tv')


def _tmdb_discover(request, media_type):
    genre_id = request.GET.get('genre')
    page = request.GET.get('page', 1)

    url = f'https://api.themoviedb.org/3/discover/{media_type}'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'language': 'ko-KR',
        'include_adult': 'false',
        'sort_by': 'popularity.desc',
        'watch_region': 'KR',
        'page': page,
    }

    if genre_id:
        params['with_genres'] = genre_id

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        movies = []
        for item in data.get('results', []):
            movies.append({
                'tmdb_id': item.get('id'),
                'title': item.get('title') or item.get('name') or item.get('original_title') or item.get('original_name'),
                'overview': item.get('overview') or '줄거리 정보가 아직 없습니다.',
                'release_date': item.get('release_date') or item.get('first_air_date') or '',
                'rating': item.get('vote_average') or 0,
                'poster_url': (
                    f"https://image.tmdb.org/t/p/w300{item.get('poster_path')}"
                    if item.get('poster_path')
                    else None
                ),
            })

        return JsonResponse({
            'page': data.get('page', 1),
            'total_pages': data.get('total_pages', 1),
            'results': movies,
        }, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
                'profile_url': _tmdb_image(person.get('profile_path'), 'w185'),
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
            'poster_url': _tmdb_image(detail.get('poster_path'), 'w500'),
            'backdrop_url': _tmdb_image(detail.get('backdrop_path'), 'w1280'),
            'cast': cast,
        }

        payload = {
            'movie': movie,
            'providers': get_streaming_providers(tmdb_id, media_type),
        }
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code if err.response is not None else 500
        return JsonResponse({'error': f'TMDB API HTTP 에러: {err}'}, status=status_code)
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


def _tmdb_image(path, size):
    if not path:
        return None
    return f'https://image.tmdb.org/t/p/{size}{path}'


def _get_streaming_providers(tmdb_id, media_type):
    data = _fetch_streaming_availability(tmdb_id, media_type)
    return _parse_streaming_providers(data)


def _kr_local_present(providers):
    return any((p.get('service') or '').lower() in wm.KR_LOCAL_SERVICES for p in providers)


def _merge_providers(primary, secondary):
    """Merge two provider lists, de-duplicating by (service name, type)."""
    seen = {((p.get('service') or '').lower(), p.get('type')) for p in primary}
    merged = list(primary)
    for prov in secondary:
        key = ((prov.get('service') or '').lower(), prov.get('type'))
        if key not in seen:
            seen.add(key)
            merged.append(prov)
    return sorted(merged, key=lambda x: _PROVIDER_PRIORITY.get(x.get('type'), 99))


def _sync_content_platforms(content, providers):
    """Persist availability rows for providers that map to a known Platform."""
    name_map = {p.name.lower(): p for p in Platform.objects.all()}
    for prov in providers:
        platform = name_map.get((prov.get('service') or '').lower())
        source_type = _TYPE_TO_SOURCE.get(prov.get('type'))
        if not platform or not source_type:
            continue
        ContentPlatform.objects.update_or_create(
            content=content, platform=platform, source_type=source_type,
            defaults={
                'deeplink_url': prov.get('link') or '',
                'price': prov.get('price'),
                'is_available': True,
            },
        )


def _decorate_providers(providers):
    """Attach local icon URLs and normalize display names for known services."""
    decorated = []
    for prov in providers:
        prov = dict(prov)
        key = (prov.get('service') or '').lower().strip()
        match = _PLATFORM_ICONS.get(key)
        if match:
            display_name, filename = match
            prov['display_name'] = display_name
            prov['icon_url'] = f'{settings.MEDIA_URL}{filename}'
        decorated.append(prov)
    return decorated


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


def get_streaming_providers(tmdb_id, media_type, allow_watchmode=True, force_refresh=False):
    """
    Resolve per-title KR streaming availability with a 24h DB cache.

    RapidAPI streaming-availability is the primary source. Watchmode is only
    queried (to fill KR gaps: TVING/Watcha/Wavve or missing titles) when
    ``allow_watchmode`` is True — reserved for detail-page views so that
    hovering across a list does not burn the Watchmode free-tier budget.
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
        providers = content.sources_cache or []
        # A title first cached from a list hover (RapidAPI only) can still be
        # enriched on its detail view without resetting the cache window.
        if (
            allow_watchmode and not content.watchmode_checked
            and not _kr_local_present(providers)
            and wm.is_configured() and WatchmodeUsage.can_call()
        ):
            providers, calls = _augment_with_watchmode(content, tmdb_id, media_type, providers)
            if calls:
                WatchmodeUsage.increment(calls)
            content.sources_cache = providers
            content.watchmode_checked = True
            content.save(update_fields=['sources_cache', 'watchmode_checked', 'watchmode_id'])
            _sync_content_platforms(content, providers)
        return _decorate_providers(providers)

    # Cache miss / expired: refresh from RapidAPI (primary).
    try:
        providers = _parse_streaming_providers(
            _fetch_streaming_availability(tmdb_id, media_type)
        )
    except Exception as exc:  # noqa: BLE001 - never let availability break the page
        print(f'RapidAPI availability failed for {media_type}/{tmdb_id}: {exc}', flush=True)
        providers = []

    watchmode_checked = False
    needs_watchmode = not providers or not _kr_local_present(providers)
    if allow_watchmode and needs_watchmode and wm.is_configured() and WatchmodeUsage.can_call():
        providers, calls = _augment_with_watchmode(content, tmdb_id, media_type, providers)
        if calls:
            WatchmodeUsage.increment(calls)
        watchmode_checked = True

    content.sources_cache = providers
    content.sources_synced_at = timezone.now()
    content.watchmode_checked = watchmode_checked
    content.save(update_fields=[
        'sources_cache', 'sources_synced_at', 'watchmode_checked', 'watchmode_id',
    ])
    _sync_content_platforms(content, providers)

    return _decorate_providers(providers)


def _fetch_streaming_availability(tmdb_id, media_type):
    rapidapi_key = getattr(settings, 'RAPIDAPI_KEY', '')
    formatted_id = f"{media_type}/{tmdb_id}"
    url = f"https://streaming-availability.p.rapidapi.com/shows/{formatted_id}"
    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "streaming-availability.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params={"country": "kr"})
    if response.status_code == 404:
        return {}
    response.raise_for_status()

    data = response.json()
    print("=== Streaming Availability 원본 JSON ===")
    print(data, flush=True)
    return data


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
                'type_label': _provider_type_label(provider_type),
                'expires_on': option.get('expiresOn'),
                'link': option.get('videoLink') or option.get('link'),
                'icon_url': _find_image_url(service),
            })

    priority = {'subscription': 0, 'free': 1, 'ads': 2, 'rent': 3, 'buy': 4, 'addon': 5}
    return sorted(providers, key=lambda provider: priority.get(provider.get('type'), 99))


def _provider_type_label(provider_type):
    labels = {
        'subscription': '구독',
        'rent': '대여',
        'buy': '구매',
        'free': '무료',
        'ads': '광고 포함',
    }
    return labels.get(provider_type, '기타')


def _find_image_url(value):
    if isinstance(value, str) and value.startswith('http'):
        return value
    if isinstance(value, dict):
        for key in ('lightThemeImage', 'darkThemeImage', 'whiteImage', 'imageUrl', 'url'):
            found = _find_image_url(value.get(key))
            if found:
                return found
        for child in value.values():
            found = _find_image_url(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_image_url(child)
            if found:
                return found
    return None

# 2. 영화/TV 검색 API (TMDB)
def tmdb_search(request):
    query = request.GET.get('query')
    if not query:
        return JsonResponse({'results': []})

    url = 'https://api.themoviedb.org/3/search/multi'
    params = {
        'api_key': settings.TMDB_API_KEY,
        'query': query,
        'language': 'ko-KR',
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
                'poster_url': (f"https://image.tmdb.org/t/p/w200{item.get('poster_path')}" if item.get('poster_path') else None)
            })
        return JsonResponse({'results': results}, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# 3. 스트리밍 정보 및 만료일 API (RapidAPI)
def api_streaming_info(request):
    tmdb_id = request.GET.get('tmdb_id')
    # TMDB에서 넘어오는 'movie' 또는 'tv' 
    media_type = request.GET.get('media_type')
    
    if not tmdb_id or not media_type:
        return JsonResponse({'error': '파라미터 누락'}, status=400)

    try:
        # List-grid hover: RapidAPI only (cheap). Watchmode enrichment is
        # reserved for the detail page to protect the monthly free-tier budget.
        payload = {
            'providers': get_streaming_providers(tmdb_id, media_type, allow_watchmode=False),
        }
        return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({'error': f"서버 에러: {str(e)}"}, status=500)
