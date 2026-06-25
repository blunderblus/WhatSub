from django.conf import settings

# Normalized name (lowercase) -> (display name, icon filename)
PLATFORM_ICON_ALIASES = {
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
    # Coupang WOW membership includes Coupang Play — same logo.
    'coupang': ('Coupang Play', 'CoupangPlay_icon.png'),
    'coupang play': ('Coupang Play', 'CoupangPlay_icon.png'),
    'coupang wow': ('Coupang Play', 'CoupangPlay_icon.png'),
    'coupangplay': ('Coupang Play', 'CoupangPlay_icon.png'),
    'tving': ('TVING', 'TVING_icon.png'),
    'wavve': ('Wavve', 'Wavve_icon.png'),
    'watcha': ('Watcha', 'Watcha_icon.webp'),
    'spotv': ('SPOTV', 'SpotvNow_icon.png'),
    'spotv now': ('SPOTV', 'SpotvNow_icon.png'),
    'spotvnow': ('SPOTV', 'SpotvNow_icon.png'),
    'icloud+': ('iCloud+', 'iCloudPlus_icon.png'),
    'icloud': ('iCloud+', 'iCloudPlus_icon.png'),
    'icloud plus': ('iCloud+', 'iCloudPlus_icon.png'),
}


def absolute_media_url(filename):
    """Absolute URL for local media files (required when frontend is on another origin)."""
    if not filename:
        return ''
    base = settings.BACKEND_URL.rstrip('/')
    media = settings.MEDIA_URL if settings.MEDIA_URL.startswith('/') else f'/{settings.MEDIA_URL}'
    if not media.endswith('/'):
        media = f'{media}/'
    return f'{base}{media}{filename}'


def platform_icon_url(name):
    match = PLATFORM_ICON_ALIASES.get((name or '').lower().strip())
    filename = match[1] if match else None
    return absolute_media_url(filename) if filename else ''
