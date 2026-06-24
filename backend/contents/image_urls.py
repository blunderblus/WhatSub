"""Image URL helpers for external content providers."""

TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'


def tmdb_image_url(path, size):
    if not path:
        return None
    return f'{TMDB_IMAGE_BASE}/{size}{path}'


def find_nested_image_url(value):
    """Find the first URL-like image value in nested API payloads."""
    if isinstance(value, str) and value.startswith('http'):
        return value
    if isinstance(value, dict):
        for key in ('lightThemeImage', 'darkThemeImage', 'whiteImage', 'imageUrl', 'url'):
            found = find_nested_image_url(value.get(key))
            if found:
                return found
        for child in value.values():
            found = find_nested_image_url(child)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_nested_image_url(child)
            if found:
                return found
    return None
