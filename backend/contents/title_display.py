"""Title/poster enrichment for cache and personal score display."""
import logging

from . import tmdb_client
from .models import Content, MediaType, TitleMeta

logger = logging.getLogger(__name__)

TMDB_POSTER_BASE = 'https://image.tmdb.org/t/p/w500'


def poster_url_from_path(poster_path):
    if not poster_path:
        return ''
    if poster_path.startswith('http'):
        return poster_path
    return f'{TMDB_POSTER_BASE}{poster_path}'


def title_from_discover_item(item):
    return (
        item.get('title') or item.get('name')
        or item.get('original_title') or item.get('original_name') or ''
    )


def upsert_title_display(tmdb_id, media_type, title='', poster_url=''):
    """Persist display fields on TitleMeta and Content."""
    if title or poster_url:
        TitleMeta.objects.update_or_create(
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={
                'title': title,
                'poster_url': poster_url,
            },
        )
        content, _ = Content.objects.get_or_create(
            tmdb_id=tmdb_id,
            defaults={'title': title, 'content_type': media_type, 'poster_url': poster_url},
        )
        updates = {}
        if title and not (content.korean_title or content.title):
            updates['title'] = title
        if poster_url and not content.poster_url:
            updates['poster_url'] = poster_url
        if content.content_type not in ('movie', 'tv'):
            updates['content_type'] = media_type
        if updates:
            for k, v in updates.items():
                setattr(content, k, v)
            content.save(update_fields=list(updates.keys()))


def _fetch_from_tmdb(tmdb_id, media_type):
    try:
        data = tmdb_client.fetch_title_brief(tmdb_id, media_type)
    except Exception as exc:
        logger.warning('TMDB title fetch failed %s/%s: %s', media_type, tmdb_id, exc)
        return '', ''
    title = data.get('title') or ''
    poster_url = data.get('poster_url') or ''
    upsert_title_display(tmdb_id, media_type, title=title, poster_url=poster_url)
    return title, poster_url


def get_title_display_map(keys, max_tmdb_fetches=40):
    """
    Build {(tmdb_id, media_type): {title, poster_url, vote_average, popularity}}.
    Fetches TMDB for missing titles up to max_tmdb_fetches.
    """
    if not keys:
        return {}

    key_list = list(keys)
    tmdb_ids = {k[0] for k in key_list}
    content_by_tmdb = {c.tmdb_id: c for c in Content.objects.filter(tmdb_id__in=tmdb_ids)}

    meta_rows = TitleMeta.objects.filter(
        tmdb_id__in=[k[0] for k in key_list],
    )
    meta_by_key = {(m.tmdb_id, m.media_type): m for m in meta_rows}

    result = {}
    fetch_budget = max_tmdb_fetches

    for tmdb_id, media_type in key_list:
        meta = meta_by_key.get((tmdb_id, media_type))
        content = content_by_tmdb.get(tmdb_id)

        title = ''
        poster_url = ''
        if meta and meta.title:
            title = meta.title
            poster_url = meta.poster_url or ''
        if content:
            title = title or content.korean_title or content.title or ''
            poster_url = poster_url or content.poster_url or ''

        if (not title or not poster_url) and fetch_budget > 0:
            fetch_budget -= 1
            fetched_title, fetched_poster = _fetch_from_tmdb(tmdb_id, media_type)
            title = title or fetched_title
            poster_url = poster_url or fetched_poster
            meta = TitleMeta.objects.filter(tmdb_id=tmdb_id, media_type=media_type).first()

        detail_type = 'movies' if media_type == MediaType.MOVIE else 'shows'
        result[(tmdb_id, media_type)] = {
            'tmdb_id': tmdb_id,
            'media_type': media_type,
            'title': title or f'작품 #{tmdb_id}',
            'poster_url': poster_url,
            'vote_average': meta.vote_average if meta else None,
            'popularity': meta.popularity if meta else None,
            'detail_path': f'/contents/{detail_type}/{tmdb_id}',
        }

    return result


def title_payload_from_map(tmdb_id, media_type, display_map, *, is_exclusive=False):
    base = display_map.get((tmdb_id, media_type), {})
    return {
        'tmdb_id': tmdb_id,
        'media_type': media_type,
        'title': base.get('title') or f'작품 #{tmdb_id}',
        'poster_url': base.get('poster_url') or '',
        'vote_average': base.get('vote_average'),
        'popularity': base.get('popularity'),
        'is_exclusive': is_exclusive,
        'detail_path': base.get('detail_path') or (
            f'/contents/{"movies" if media_type == "movie" else "shows"}/{tmdb_id}'
        ),
    }
