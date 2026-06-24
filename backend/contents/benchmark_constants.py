"""Shared benchmark constants (avoids circular imports)."""
from django.conf import settings

from .streaming_provider_display import PLATFORM_ICON_ALIASES

GENRE_NAMES = {
    28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
    99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
    27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance', 878: 'Sci-Fi',
    53: 'Thriller', 10752: 'War', 37: 'Western', 10770: 'TV Movie',
    10759: 'Action & Adventure', 10762: 'Kids', 10763: 'News', 10764: 'Reality',
    10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics',
}

AXIS_LABELS = {
    'availability': '콘텐츠',
    'exclusivity': '독점작',
    'quality': '고품질',
    'price': '가격',
    'accessibility': '접근성',
}


def platform_icon(name):
    match = PLATFORM_ICON_ALIASES.get((name or '').lower().strip())
    filename = match[1] if match else None
    return f'{settings.MEDIA_URL}{filename}' if filename else ''
