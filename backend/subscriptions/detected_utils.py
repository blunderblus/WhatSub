"""Enrich LLM-detected subscription rows with official catalog metadata."""

from .platform_utils import resolve_official_platform


def enrich_detected_subscription(sub: dict) -> dict:
    """Attach platform_id / platform_matched for catalog-aware UIs."""
    out = dict(sub or {})
    raw_name = (out.get('platform') or '').strip()
    official = resolve_official_platform(
        name=raw_name,
        platform_id=out.get('platform_id'),
    )
    out['platform_id'] = official.id if official else None
    out['platform_matched'] = bool(official)
    out['catalog_platform_name'] = official.name if official else raw_name
    out['custom'] = not bool(official)
    if official:
        out['platform'] = official.name
    return out
