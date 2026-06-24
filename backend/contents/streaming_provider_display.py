"""Provider normalization, ordering, and display decoration."""

from django.conf import settings

from subscriptions.platform_icons import PLATFORM_ICON_ALIASES

PROVIDER_PRIORITY = {
    'subscription': 0,
    'free': 1,
    'ads': 2,
    'rent': 3,
    'buy': 4,
    'addon': 5,
}

CONTENT_PLATFORM_SOURCE_TYPES = {
    'subscription': 'sub',
    'free': 'free',
    'rent': 'rent',
    'buy': 'buy',
}

PROVIDER_TYPE_LABELS = {
    'subscription': '\uad6c\ub3c5',
    'rent': '\ub300\uc5ec',
    'buy': '\uad6c\ub9e4',
    'free': '\ubb34\ub8cc',
    'ads': '\uad11\uace0 \ud3ec\ud568',
}

def provider_type_label(provider_type):
    return PROVIDER_TYPE_LABELS.get(provider_type, '\uae30\ud0c0')


def normalized_service(provider):
    service = (
        provider.get('service')
        or provider.get('display_name')
        or ''
    ).lower().strip()
    match = PLATFORM_ICON_ALIASES.get(service)
    return match[0].lower() if match else service


def provider_key(provider):
    return (normalized_service(provider), provider.get('type') or 'subscription')


def provider_sort_key(provider):
    return (
        PROVIDER_PRIORITY.get(provider.get('type'), 99),
        normalized_service(provider),
    )


def sort_providers(providers):
    return sorted(providers, key=provider_sort_key)


def decorate_providers(providers):
    """Attach local icon URLs and normalize display names for known services."""
    decorated = []
    for provider in providers:
        provider = dict(provider)
        key = (provider.get('service') or '').lower().strip()
        match = PLATFORM_ICON_ALIASES.get(key)
        if match:
            display_name, filename = match
            provider['display_name'] = display_name
            provider['icon_url'] = f'{settings.MEDIA_URL}{filename}'
        decorated.append(provider)
    return decorated
