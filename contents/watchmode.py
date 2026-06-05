"""
Watchmode API client.

Used as a supplement to RapidAPI streaming-availability: when RapidAPI returns
no results or is missing Korean local services (TVING / Watcha / Wavve),
Watchmode is queried to fill the gaps for the KR region.

Free tier is 2,500 requests/month, so callers must guard with
``WatchmodeUsage.can_call()`` and record usage with ``WatchmodeUsage.increment()``.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

WATCHMODE_BASE = 'https://api.watchmode.com/v1'
REQUEST_TIMEOUT = 10

# Korean local services we specifically rely on Watchmode to cover.
KR_LOCAL_SERVICES = {'tving', 'watcha', 'wavve'}

# Watchmode source `type` -> our internal provider type.
_TYPE_MAP = {
    'sub': 'subscription',
    'subscription': 'subscription',
    'free': 'free',
    'rent': 'rent',
    'buy': 'buy',
    'tve': 'subscription',
}

_TYPE_LABELS = {
    'subscription': '구독',
    'rent': '대여',
    'buy': '구매',
    'free': '무료',
}


def _api_key():
    return getattr(settings, 'WATCHMODE_API_KEY', '') or ''


def is_configured():
    return bool(_api_key())


def _search_field(media_type):
    return 'tmdb_tv_id' if media_type == 'tv' else 'tmdb_movie_id'


def resolve_watchmode_id(tmdb_id, media_type):
    """
    Map a TMDB id to a Watchmode title id (one API call).
    Returns the Watchmode id (int) or None.
    """
    if not is_configured():
        return None
    try:
        resp = requests.get(
            f'{WATCHMODE_BASE}/search/',
            params={
                'apiKey': _api_key(),
                'search_field': _search_field(media_type),
                'search_value': tmdb_id,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Watchmode search failed for %s/%s: %s', media_type, tmdb_id, exc)
        return None

    results = data.get('title_results') or []
    if results and isinstance(results, list):
        return results[0].get('id')
    return None


def fetch_sources(watchmode_id, region='KR'):
    """Fetch raw streaming sources for a Watchmode title (one API call)."""
    if not is_configured() or not watchmode_id:
        return []
    try:
        resp = requests.get(
            f'{WATCHMODE_BASE}/title/{watchmode_id}/sources/',
            params={'apiKey': _api_key(), 'regions': region},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning('Watchmode sources failed for id=%s: %s', watchmode_id, exc)
        return []
    return data if isinstance(data, list) else []


def parse_sources(raw_sources, region='KR'):
    """Normalize Watchmode sources into the provider dict shape the frontend expects."""
    providers = []
    seen = set()
    for src in raw_sources:
        if not isinstance(src, dict):
            continue
        if region and src.get('region') and src.get('region') != region:
            continue

        name = src.get('name')
        if not name:
            continue

        raw_type = (src.get('type') or '').lower()
        ptype = _TYPE_MAP.get(raw_type, raw_type or 'subscription')
        key = (name.lower(), ptype)
        if key in seen:
            continue
        seen.add(key)

        providers.append({
            'service': name,
            'service_id': src.get('source_id'),
            'addon': None,
            'display_name': name,
            'type': ptype,
            'type_label': _TYPE_LABELS.get(ptype, '기타'),
            'expires_on': None,
            'link': src.get('web_url') or src.get('ios_url') or src.get('android_url'),
            'icon_url': None,
            'price': src.get('price'),
            'source': 'watchmode',
        })
    return providers
