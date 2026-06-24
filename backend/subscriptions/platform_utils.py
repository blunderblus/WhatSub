"""Match LLM / user input to official Platform rows in our catalog."""

from .models import Platform

# Common aliases from receipts / LLM output → canonical Platform.name
_PLATFORM_ALIASES = {
    'prime video': 'Amazon Prime Video',
    'amazon prime video': 'Amazon Prime Video',
    'amazon prime': 'Amazon Prime Video',
    'prime': 'Amazon Prime Video',
    'apple tv+': 'Apple TV+',
    'apple tv plus': 'Apple TV+',
    'apple tv': 'Apple TV+',
    'appletv+': 'Apple TV+',
    'appletv': 'Apple TV+',
    'apple one': 'Apple One',
    'apple music': 'Apple Music',
    'apple arcade': 'Apple Arcade',
    'icloud+': 'iCloud+',
    'icloud plus': 'iCloud+',
    'disney plus': 'Disney+',
    'disney+': 'Disney+',
    'disney': 'Disney+',
    'youtube premium': 'YouTube Premium',
    'youtube': 'YouTube Premium',
    'spotify': 'Spotify',
    'chatgpt plus': 'ChatGPT Plus',
    'chatgpt': 'ChatGPT Plus',
    'openai': 'ChatGPT Plus',
    'coupang play': 'Coupang Play',
    'coupang wow': 'Coupang',
    'coupang': 'Coupang',
    'coupangplay': 'Coupang Play',
    'netflix': 'Netflix',
    'wavve': 'Wavve',
    'watcha': 'Watcha',
    '티빙': 'TVING',
    'tving': 'TVING',
    'spotv now': 'SPOTV',
    'spotv': 'SPOTV',
}


def resolve_official_platform(name=None, platform_id=None):
    """
    Return a Platform instance if the name/id matches our official catalog.
    Returns None for unknown / unsupported services.
    """
    if platform_id:
        platform = Platform.objects.filter(pk=platform_id).first()
        if platform:
            return platform

    raw = (name or '').strip()
    if not raw:
        return None

    lowered = raw.lower()
    alias_target = _PLATFORM_ALIASES.get(lowered)
    if alias_target:
        platform = Platform.objects.filter(name__iexact=alias_target).first()
        if platform:
            return platform

    platform = Platform.objects.filter(name__iexact=raw).first()
    if platform:
        return platform

    official = {p.name.lower(): p for p in Platform.objects.all()}
    if lowered in official:
        return official[lowered]

    for key, platform in official.items():
        if lowered in key or key in lowered:
            return platform

    return None
