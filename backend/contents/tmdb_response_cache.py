"""Small cache layer for TMDB JSON responses used by content lists."""
import copy
import hashlib
import json

from django.core.cache import cache

TMDB_DISCOVER_CACHE_TTL = 60 * 60 * 6
TMDB_GENRE_CACHE_TTL = 60 * 60 * 24


def _cache_key(namespace, url, params):
    payload = {
        'url': url,
        'params': sorted((params or {}).items()),
    }
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f'contents:tmdb:{namespace}:{digest}'


def get_or_fetch_tmdb_json(namespace, url, params, fetcher, timeout):
    key = _cache_key(namespace, url, params)
    cached = cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)

    data = fetcher()
    cache.set(key, copy.deepcopy(data), timeout)
    return data
