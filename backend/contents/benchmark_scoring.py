"""Platform benchmark scoring pipeline (5 axes + snapshot write)."""
import json
import logging
from collections import defaultdict
from datetime import date

from django.db.models import Count, Q
from django.utils import timezone

from subscriptions.models import Platform, SubscriptionPlan

from detector.ai_client import resolve_scoring_model
from .benchmark_cache import aggregate_platform_genre_stats
from .llm_judgment import build_cache_key, get_llm_judgment, is_configured
from .models import (
    LLMJudgmentCache,
    PlatformBenchmarkSnapshot,
    StreamingCache,
    TitleMeta,
)

logger = logging.getLogger(__name__)

QUALITY_VOTE_AVERAGE_MIN = 7.0
QUALITY_VOTE_COUNT_MIN = 500

CONFIDENCE_HIGH_PLATFORM_TITLES = 100
CONFIDENCE_MEDIUM_PLATFORM_TITLES = 30
CONFIDENCE_HIGH_GLOBAL_TITLES = 300
CONFIDENCE_MEDIUM_GLOBAL_TITLES = 150

QUALITY_MAP = {'SD': 0.25, 'HD': 0.5, 'FHD': 0.75, '4K': 1.0}

EXCLUSIVITY_LLM_SCHEMA = (
    '{"weights": [{"tmdb_id": int, "media_type": "movie|tv", '
    '"trending_weight": float 0.0-1.0}]}'
)
PRICE_LLM_SCHEMA = (
    '{"judgments": [{"plan_id": int, "is_beneficial": bool, "reason": string}]}'
)


def normalize_scores(raw_by_platform):
    """Min-max normalize platform raw metrics to 0.0-1.0."""
    if not raw_by_platform:
        return {}
    values = list(raw_by_platform.values())
    lo, hi = min(values), max(values)
    if hi == lo:
        return {pid: (1.0 if v > 0 else 0.0) for pid, v in raw_by_platform.items()}
    return {pid: (v - lo) / (hi - lo) for pid, v in raw_by_platform.items()}


def streaming_platforms():
    """OTT platforms: streaming category and/or observed in StreamingCache."""
    return (
        Platform.objects
        .filter(
            Q(category__name='스트리밍')
            | Q(tmdb_provider_id__isnull=False)
            | Q(streaming_cache_entries__available=True),
        )
        .distinct()
        .order_by('name')
    )


def _title_meta_lookup():
    lookup = {}
    for row in TitleMeta.objects.values('tmdb_id', 'media_type', 'vote_average', 'vote_count', 'popularity'):
        lookup[(row['tmdb_id'], row['media_type'])] = row
    return lookup


def _global_distinct_title_count():
    return (
        StreamingCache.objects
        .filter(available=True)
        .values('tmdb_id', 'media_type')
        .distinct()
        .count()
    )


def compute_confidence_level(platform_title_count, global_title_count):
    if (
        platform_title_count >= CONFIDENCE_HIGH_PLATFORM_TITLES
        and global_title_count >= CONFIDENCE_HIGH_GLOBAL_TITLES
    ):
        return PlatformBenchmarkSnapshot.ConfidenceLevel.HIGH
    if (
        platform_title_count >= CONFIDENCE_MEDIUM_PLATFORM_TITLES
        and global_title_count >= CONFIDENCE_MEDIUM_GLOBAL_TITLES
    ):
        return PlatformBenchmarkSnapshot.ConfidenceLevel.MEDIUM
    return PlatformBenchmarkSnapshot.ConfidenceLevel.LOW


def compute_availability_raw():
    rows = (
        StreamingCache.objects
        .filter(available=True)
        .values('platform_id')
        .annotate(title_count=Count('tmdb_id', distinct=True))
    )
    return {r['platform_id']: r['title_count'] for r in rows}


def compute_quality_raw(meta_lookup):
    """Asymmetric count-based quality (never average-based)."""
    counts = defaultdict(int)
    rows = StreamingCache.objects.filter(available=True).values('platform_id', 'tmdb_id', 'media_type')
    for row in rows:
        meta = meta_lookup.get((row['tmdb_id'], row['media_type']))
        if not meta:
            continue
        if (
            meta['vote_average'] >= QUALITY_VOTE_AVERAGE_MIN
            and meta['vote_count'] >= QUALITY_VOTE_COUNT_MIN
        ):
            counts[row['platform_id']] += 1
    return dict(counts)


def _exclusive_titles_by_platform(meta_lookup):
    """Titles on exactly one platform in cache, grouped by that platform."""
    single_keys = set(
        StreamingCache.objects
        .filter(available=True)
        .values('tmdb_id', 'media_type')
        .annotate(n=Count('platform', distinct=True))
        .filter(n=1)
        .values_list('tmdb_id', 'media_type')
    )
    by_platform = defaultdict(list)
    for row in StreamingCache.objects.filter(available=True).values('platform_id', 'tmdb_id', 'media_type'):
        key = (row['tmdb_id'], row['media_type'])
        if key not in single_keys:
            continue
        meta = meta_lookup.get(key, {})
        by_platform[row['platform_id']].append({
            'tmdb_id': row['tmdb_id'],
            'media_type': row['media_type'],
            'popularity': meta.get('popularity') or 0,
            'vote_average': meta.get('vote_average') or 0,
        })
    return by_platform


def _llm_exclusivity_weights(platform, titles, snapshot_date, use_llm=True):
    """Return { (tmdb_id, media_type): trending_weight }."""
    if not titles:
        return {}

    if not use_llm or not is_configured():
        return {(t['tmdb_id'], t['media_type']): 0.5 for t in titles}

    payload = json.dumps(titles, ensure_ascii=False)
    prompt = (
        f'Platform: {platform.name}\n'
        f'These titles are exclusive to {platform.name} within our observed KR streaming cache.\n'
        f'Assign trending_weight (0.0-1.0) for each — cultural buzz, awards, word-of-mouth — '
        f'without changing vote_average or popularity values.\n'
        f'Titles JSON:\n{payload}'
    )
    cache_key = build_cache_key(
        LLMJudgmentCache.JudgmentType.EXCLUSIVITY_WEIGHT,
        snapshot_date,
        platform.id,
        prompt,
    )
    result = get_llm_judgment(
        cache_key, prompt, snapshot_date,
        LLMJudgmentCache.JudgmentType.EXCLUSIVITY_WEIGHT,
        target_id=str(platform.id),
        schema_hint=EXCLUSIVITY_LLM_SCHEMA,
        model=resolve_scoring_model(),
    )
    weights = {}
    if result and isinstance(result.get('weights'), list):
        for item in result['weights']:
            key = (item.get('tmdb_id'), item.get('media_type'))
            if key[0] is not None and key[1]:
                w = float(item.get('trending_weight', 0.5))
                weights[key] = max(0.0, min(1.0, w))
    for t in titles:
        key = (t['tmdb_id'], t['media_type'])
        weights.setdefault(key, 0.5)
    return weights


def compute_exclusivity_raw(meta_lookup, snapshot_date, use_llm=True):
    """
    LLM-adjusted exclusivity: sum(popularity_normalized * trending_weight) per platform.
    """
    by_platform = _exclusive_titles_by_platform(meta_lookup)
    raw = {}

    all_pops = [
        t['popularity'] for titles in by_platform.values() for t in titles if t['popularity'] > 0
    ]
    pop_max = max(all_pops) if all_pops else 1.0

    for platform_id, titles in by_platform.items():
        platform = Platform.objects.get(pk=platform_id)
        weights = _llm_exclusivity_weights(platform, titles, snapshot_date, use_llm=use_llm)
        score_sum = 0.0
        for t in titles:
            pop_norm = (t['popularity'] / pop_max) if pop_max else 0.0
            tw = weights.get((t['tmdb_id'], t['media_type']), 0.5)
            score_sum += pop_norm * tw
        raw[platform_id] = score_sum

    return raw


def _llm_beneficial_plan_ids(platform, plans, snapshot_date, use_llm=True):
    if not plans:
        return set()
    if not use_llm or not is_configured():
        return {p.id for p in plans if p.price > 0 and not p.requires_membership_id}

    plan_data = [
        {
            'plan_id': p.id,
            'plan_name': p.plan_name,
            'price': p.price,
            'billing_period': p.billing_period,
            'max_streams': p.max_streams,
            'max_quality': p.max_quality,
            'has_download': p.has_download,
            'has_ads': p.has_ads,
            'is_bundle': p.is_bundle,
            'notes': (p.notes or '')[:400],
        }
        for p in plans
    ]
    prompt = (
        f'Platform: {platform.name}\n'
        f'Judge whether each plan is genuinely beneficial to an average KR consumer.\n'
        f'Consider price-to-spec ratio and feasibility of eligibility (affiliate/card/carrier).\n'
        f'Plans JSON:\n{json.dumps(plan_data, ensure_ascii=False)}'
    )
    cache_key = build_cache_key(
        LLMJudgmentCache.JudgmentType.PRICE_BENEFICIAL,
        snapshot_date,
        platform.id,
        prompt,
    )
    result = get_llm_judgment(
        cache_key, prompt, snapshot_date,
        LLMJudgmentCache.JudgmentType.PRICE_BENEFICIAL,
        target_id=str(platform.id),
        schema_hint=PRICE_LLM_SCHEMA,
        model=resolve_scoring_model(),
    )
    beneficial = set()
    if result and isinstance(result.get('judgments'), list):
        for item in result['judgments']:
            if item.get('is_beneficial') and item.get('plan_id') is not None:
                beneficial.add(int(item['plan_id']))
    return beneficial


def compute_price_raw(platforms_qs, snapshot_date, use_llm=True):
    """bundle_count * 0.3 + beneficial_count * 0.7 (pre-normalization components summed)."""
    raw = {}
    for platform in platforms_qs:
        plans = list(SubscriptionPlan.objects.filter(platform=platform))
        bundle_count = sum(1 for p in plans if p.is_bundle)
        non_bundle = [p for p in plans if not p.is_bundle]
        beneficial = _llm_beneficial_plan_ids(platform, non_bundle, snapshot_date, use_llm=use_llm)
        beneficial_count = len(beneficial)
        raw[platform.id] = bundle_count * 0.3 + beneficial_count * 0.7
    return raw


def compute_accessibility_scores(platforms_qs):
    """Best-tier plan accessibility per platform (0.0-1.0, no cross-platform normalize)."""
    scores = {}
    for platform in platforms_qs:
        plans = SubscriptionPlan.objects.filter(platform=platform, is_bundle=False)
        best = 0.0
        for p in plans:
            q = QUALITY_MAP.get(p.max_quality, 0.5)
            streams = min(p.max_streams / 4.0, 1.0)
            dl = 0.15 if p.has_download else 0.0
            ads = -0.1 if p.has_ads else 0.0
            tier = streams * 0.4 + q * 0.45 + dl + ads
            best = max(best, tier)
        scores[platform.id] = round(min(max(best, 0.0), 1.0), 4)
    return scores


def compute_value_score(scores):
    """Equal-weight combination of five normalized axes (TBD in UX)."""
    keys = ('availability', 'exclusivity', 'quality', 'price', 'accessibility')
    parts = [scores.get(k, 0.0) or 0.0 for k in keys]
    return round(sum(parts) / len(keys), 4)


def run_benchmark_batch(snapshot_date=None, use_llm=True, log=logger.info):
    """
    Monthly benchmark pipeline:
      1) PlatformGenreStats aggregation
      2) Five axis scores + confidence
      3) PlatformBenchmarkSnapshot write
    """
    snapshot_date = snapshot_date or timezone.localdate()
    platforms_qs = streaming_platforms()
    platform_ids = list(platforms_qs.values_list('id', flat=True))

    log('[benchmark] snapshot_date=%s platforms=%d', snapshot_date, len(platform_ids))

    genre_stats = aggregate_platform_genre_stats(snapshot_date=snapshot_date)
    log('[benchmark] genre stats rows=%d', genre_stats['platform_genre_rows'])

    meta_lookup = _title_meta_lookup()
    global_titles = _global_distinct_title_count()
    log('[benchmark] global distinct titles in cache=%d', global_titles)

    avail_raw = compute_availability_raw()
    quality_raw = compute_quality_raw(meta_lookup)
    exclusivity_raw = compute_exclusivity_raw(meta_lookup, snapshot_date, use_llm=use_llm)
    price_raw = compute_price_raw(platforms_qs, snapshot_date, use_llm=use_llm)
    accessibility = compute_accessibility_scores(platforms_qs)

    avail_scores = normalize_scores({pid: avail_raw.get(pid, 0) for pid in platform_ids})
    quality_scores = normalize_scores({pid: quality_raw.get(pid, 0) for pid in platform_ids})
    exclusivity_scores = normalize_scores({pid: exclusivity_raw.get(pid, 0) for pid in platform_ids})
    price_scores = normalize_scores({pid: price_raw.get(pid, 0) for pid in platform_ids})

    snapshots = []
    for platform in platforms_qs:
        pid = platform.id
        title_count = avail_raw.get(pid, 0)
        confidence = compute_confidence_level(title_count, global_titles)
        axis = {
            'availability': round(avail_scores.get(pid, 0.0), 4),
            'exclusivity': round(exclusivity_scores.get(pid, 0.0), 4),
            'quality': round(quality_scores.get(pid, 0.0), 4),
            'price': round(price_scores.get(pid, 0.0), 4),
            'accessibility': accessibility.get(pid, 0.0),
        }
        value = compute_value_score(axis)
        snapshots.append({
            'platform': platform,
            'confidence': confidence,
            'axis': axis,
            'value': value,
            'title_count': title_count,
        })

    PlatformBenchmarkSnapshot.objects.filter(snapshot_date=snapshot_date).delete()
    for s in snapshots:
        PlatformBenchmarkSnapshot.objects.create(
            platform=s['platform'],
            snapshot_date=snapshot_date,
            availability_score=s['axis']['availability'],
            exclusivity_score=s['axis']['exclusivity'],
            quality_score=s['axis']['quality'],
            price_score=s['axis']['price'],
            accessibility_score=s['axis']['accessibility'],
            confidence_level=s['confidence'],
            value_score=s['value'],
        )

    log('[benchmark] wrote %d PlatformBenchmarkSnapshot rows', len(snapshots))
    return {
        'snapshot_date': snapshot_date.isoformat(),
        'global_titles': global_titles,
        'platforms': [
            {
                'name': s['platform'].name,
                'confidence': s['confidence'],
                'value_score': s['value'],
                'titles': s['title_count'],
                **s['axis'],
            }
            for s in sorted(snapshots, key=lambda x: -x['value'])
        ],
    }
