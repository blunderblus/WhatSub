"""TMDB API helpers for benchmark cold-start cache warming."""
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TMDB_BASE = 'https://api.themoviedb.org/3'
WATCH_REGION = 'KR'
REQUEST_DELAY_SEC = 0.05


def _api_key():
    return settings.TMDB_API_KEY


def _get(path, params=None):
    params = dict(params or {})
    params['api_key'] = _api_key()
    url = f'{TMDB_BASE}{path}'
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SEC)
    return response.json()


def discover_popular(media_type, page=1):
    """Fetch a page of popular titles for KR watch region."""
    return _get(
        f'/discover/{media_type}',
        {
            'language': 'ko-KR',
            'include_adult': 'false',
            'sort_by': 'popularity.desc',
            'watch_region': WATCH_REGION,
            'page': page,
        },
    )


def discover_by_genre(media_type, genre_id, page=1):
    """Fetch one page of popular titles for a single TMDB genre (KR region)."""
    return _get(
        f'/discover/{media_type}',
        {
            'language': 'ko-KR',
            'include_adult': 'false',
            'sort_by': 'popularity.desc',
            'watch_region': WATCH_REGION,
            'with_genres': genre_id,
            'page': page,
        },
    )


def discover_by_provider(media_type, provider_id, page=1):
    """Fetch one page of titles available on a watch provider in KR."""
    return _get(
        f'/discover/{media_type}',
        {
            'language': 'ko-KR',
            'include_adult': 'false',
            'sort_by': 'popularity.desc',
            'watch_region': WATCH_REGION,
            'with_watch_providers': provider_id,
            'page': page,
        },
    )


def fetch_title_brief(tmdb_id, media_type):
    """Minimal title + poster for display enrichment."""
    data = _get(f'/{media_type}/{tmdb_id}', {'language': 'ko-KR'})
    title = data.get('title') or data.get('name') or data.get('original_title') or data.get('original_name') or ''
    poster_path = data.get('poster_path')
    poster_url = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else ''
    return {'title': title, 'poster_url': poster_url}


def fetch_watch_providers(tmdb_id, media_type):
    """Return KR flatrate provider ids for a title."""
    data = _get(f'/{media_type}/{tmdb_id}/watch/providers')
    region = (data.get('results') or {}).get(WATCH_REGION) or {}
    flatrate = region.get('flatrate') or []
    return [p['provider_id'] for p in flatrate if p.get('provider_id')]
