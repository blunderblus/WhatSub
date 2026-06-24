"""Full platform benchmark page payload (stats, LLM insight, plans, reviews)."""
import json
from datetime import date

from django.db.models import Avg, Count, F, Q
from subscriptions.models import Platform, SubscriptionPlan, BundleContent, AddOnPass
from subscriptions.serializers import SubscriptionPlanSerializer, AddOnPassSerializer

from .benchmark_constants import AXIS_LABELS, GENRE_NAMES, platform_icon
from .benchmark_scoring import compute_availability_raw
from .benchmark_views import _resolve_snapshot_date
from .llm_judgment import get_llm_judgment, is_configured
from .models import (
    LLMJudgmentCache,
    PlatformBenchmarkSnapshot,
    PlatformGenreStats,
    PlatformUserReview,
)
from .personal_scoring import _exclusive_highlights, _exclusive_titles_by_platform
from .review_social import (
    build_score_summary,
    community_board_preview,
    review_comment_payload,
    review_reaction_payload,
)
from .title_display import get_title_display_map

PLATFORM_INSIGHT_SCHEMA = (
    '{"summary": string, "strengths": [string], "weaknesses": [string], '
    '"best_for": string, "plan_tip": string}'
)


def _month_key(d: date) -> str:
    return d.strftime('%Y-%m')


def get_platform_llm_insight(platform, snap, snapshot_date, use_llm=True):
    """Monthly LLM insight (temperature=0, cached per platform per month)."""
    month = _month_key(snapshot_date)
    cache_key = f'platform_insight:{platform.id}:{month}'

    if not use_llm or not is_configured() or not snap:
        return None

    prompt = (
        f'Platform: {platform.name}\n'
        f'Country: {platform.country}\n'
        f'Description: {(platform.description or "")[:600]}\n'
        f'Benchmark snapshot ({snapshot_date}):\n'
        f'  value_score={snap.value_score}\n'
        f'  availability={snap.availability_score}, exclusivity={snap.exclusivity_score}\n'
        f'  quality={snap.quality_score}, price={snap.price_score}, accessibility={snap.accessibility_score}\n'
        f'  confidence={snap.confidence_level}\n'
        f'Write a concise consumer-facing insight for Korean users.\n'
        f'REQUIRED: All text fields (summary, strengths, weaknesses, best_for, plan_tip) '
        f'must be written in Korean only. Do not use English except proper nouns '
        f'(Netflix, Disney+, etc.). JSON only.'
    )
    return get_llm_judgment(
        cache_key, prompt, snapshot_date,
        LLMJudgmentCache.JudgmentType.PLATFORM_INSIGHT,
        target_id=str(platform.id),
        schema_hint=PLATFORM_INSIGHT_SCHEMA,
    )


def _user_review_payload(review, request=None):
    from community.serializers import author_payload
    payload = {
        'id': review.id,
        'score': review.score,
        'body': review.body,
        'author': author_payload(review.user),
        'created_at': review.created_at.isoformat(),
        'updated_at': review.updated_at.isoformat(),
        'is_owner': bool(
            request and request.user.is_authenticated and review.user_id == request.user.id
        ),
    }
    payload['reactions'] = review_reaction_payload(review, request)
    comments = list(review.comments.select_related('author').all())
    payload['comment_count'] = len(comments)
    payload['comments'] = [review_comment_payload(item, request) for item in comments]
    return payload


def _reviews_payload(platform, request):
    review_stats = PlatformUserReview.objects.filter(platform=platform).aggregate(
        avg_score=Avg('score'), count=Count('id'),
    )
    reviews = (
        PlatformUserReview.objects
        .filter(platform=platform)
        .select_related('user')
        .prefetch_related('reactions', 'comments__author')
        .annotate(
            like_count=Count(
                'reactions',
                filter=Q(reactions__reaction='like'),
                distinct=True,
            ),
            dislike_count=Count(
                'reactions',
                filter=Q(reactions__reaction='dislike'),
                distinct=True,
            ),
        )
        .annotate(reaction_score=F('like_count') - F('dislike_count'))
        .order_by('-reaction_score', '-updated_at')[:30]
    )
    my_review = None
    if request and request.user.is_authenticated:
        my_review = PlatformUserReview.objects.filter(
            platform=platform, user=request.user,
        ).select_related('user').prefetch_related('reactions', 'comments__author').first()
    return {
        'user_score': {
            'average': round(review_stats['avg_score'] or 0, 2),
            'count': review_stats['count'] or 0,
        },
        'score_summary': build_score_summary(platform),
        'reviews': [_user_review_payload(r, request) for r in reviews],
        'my_review': _user_review_payload(my_review, request) if my_review else None,
    }


def build_platform_page(platform_id, request=None, use_llm=True, enrich_titles=True):
    snapshot_date = _resolve_snapshot_date(request) if request else None
    if not snapshot_date:
        snapshot_date = (
            PlatformBenchmarkSnapshot.objects
            .order_by('-snapshot_date')
            .values_list('snapshot_date', flat=True)
            .first()
        )
    if not snapshot_date:
        return None

    platform = Platform.objects.filter(pk=platform_id).select_related('category').first()
    if not platform:
        return None

    snap = PlatformBenchmarkSnapshot.objects.filter(
        platform=platform, snapshot_date=snapshot_date,
    ).first()

    avail = compute_availability_raw()
    genre_rows = PlatformGenreStats.objects.filter(
        platform=platform, snapshot_date=snapshot_date,
    ).order_by('-title_count')
    genres = [
        {
            'genre_id': row.genre_id,
            'genre_name': GENRE_NAMES.get(row.genre_id, f'Genre {row.genre_id}'),
            'title_count': row.title_count,
        }
        for row in genre_rows
    ]

    plans_qs = (
        SubscriptionPlan.objects
        .filter(platform=platform)
        .select_related('platform', 'requires_membership__platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )
    regular_plans = plans_qs.filter(is_bundle=False)
    bundles = plans_qs.filter(is_bundle=True)

    related_bundle_ids = (
        BundleContent.objects
        .filter(included_platform=platform)
        .values_list('plan_id', flat=True)
        .distinct()
    )
    related_bundles = (
        SubscriptionPlan.objects
        .filter(id__in=related_bundle_ids, is_bundle=True)
        .select_related('platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )
    addon_passes = (
        AddOnPass.objects
        .filter(platform=platform)
        .prefetch_related('pricings__base_plan__platform')
        .order_by('pass_name')
    )

    plans_data = SubscriptionPlanSerializer(regular_plans, many=True).data
    bundles_data = SubscriptionPlanSerializer(bundles, many=True).data
    related_bundles_data = SubscriptionPlanSerializer(related_bundles, many=True).data
    addon_passes_data = AddOnPassSerializer(addon_passes, many=True).data

    reviews_block = _reviews_payload(platform, request)

    community_board = community_board_preview(platform, request, limit=10)

    ex_keys = _exclusive_titles_by_platform().get(platform_id, set())
    if enrich_titles and ex_keys:
        display_map = get_title_display_map(ex_keys, max_tmdb_fetches=20)
        exclusive_highlights = _exclusive_highlights(platform_id, display_map, limit=12)
    else:
        display_map = get_title_display_map(ex_keys, max_tmdb_fetches=0)
        exclusive_highlights = _exclusive_highlights(platform_id, display_map, limit=12)

    insight = get_platform_llm_insight(platform, snap, snapshot_date, use_llm=use_llm) if use_llm else None

    return {
        'snapshot_date': snapshot_date.isoformat(),
        'platform_id': platform.id,
        'name': platform.name,
        'description': platform.description,
        'category': platform.category.name if platform.category else '',
        'icon_url': platform_icon(platform.name),
        'website_url': platform.website_url,
        'title_count': avail.get(platform.id, 0),
        'value_score': snap.value_score if snap else None,
        'confidence_level': snap.confidence_level if snap else 'low',
        'scores': {
            'availability': snap.availability_score if snap else 0,
            'exclusivity': snap.exclusivity_score if snap else 0,
            'quality': snap.quality_score if snap else 0,
            'price': snap.price_score if snap else 0,
            'accessibility': snap.accessibility_score if snap else 0,
        } if snap else {},
        'axis_labels': AXIS_LABELS,
        'genres': genres,
        'plans': plans_data,
        'bundles': bundles_data,
        'related_bundles': related_bundles_data,
        'addon_passes': addon_passes_data,
        'llm_insight': insight,
        'llm_insight_month': _month_key(snapshot_date),
        **reviews_block,
        'community_board': community_board,
        'calculator_url': f'/benchmark?tab=personal&platform_id={platform.id}',
        'exclusive_highlights': exclusive_highlights,
        'content_links': {
            'movies': f'/contents/movies?platform_id={platform.id}',
            'shows': f'/contents/shows?platform_id={platform.id}',
        },
    }
