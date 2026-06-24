"""GMS proxy URL and authentication helpers."""

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings


def gms_api_key() -> str:
    return (
        getattr(settings, 'AI_API_KEY', '')
        or getattr(settings, 'GMS_KEY', '')
        or ''
    ).strip().strip("'\"")


def append_gms_key(url: str, api_key: str | None = None) -> str:
    """Append ?key=GMS_KEY (Gemini GMS docs require query-string auth)."""
    key = (api_key or gms_api_key()).strip()
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if key:
        query['key'] = key
    return urlunparse(parts._replace(query=urlencode(query)))


def gms_json_headers() -> dict:
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
