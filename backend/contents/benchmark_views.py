"""Benchmark snapshot API (served from PlatformBenchmarkSnapshot — no live API calls)."""
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from subscriptions.models import Platform

from .benchmark_constants import AXIS_LABELS, GENRE_NAMES, platform_icon
from .benchmark_scoring import compute_availability_raw
from .models import PlatformBenchmarkSnapshot, PlatformGenreStats, StreamingCache

_platform_icon = platform_icon


def _resolve_snapshot_date(request):
    raw = request.GET.get('snapshot_date')
    if raw:
        parsed = parse_date(raw)
        if parsed:
            return parsed
    return (
        PlatformBenchmarkSnapshot.objects
        .order_by('-snapshot_date')
        .values_list('snapshot_date', flat=True)
        .first()
    )


def _global_title_count():
    return (
        StreamingCache.objects
        .filter(available=True)
        .values('tmdb_id', 'media_type')
        .distinct()
        .count()
    )


def _snapshot_payload(snapshot_date, min_titles=0):
    if not snapshot_date:
        return None

    avail = compute_availability_raw()
    rows = (
        PlatformBenchmarkSnapshot.objects
        .filter(snapshot_date=snapshot_date)
        .select_related('platform')
        .order_by('-value_score', 'platform__name')
    )

    platforms = []
    for snap in rows:
        title_count = avail.get(snap.platform_id, 0)
        if min_titles and title_count < min_titles:
            continue
        platforms.append({
            'platform_id': snap.platform_id,
            'name': snap.platform.name,
            'icon_url': _platform_icon(snap.platform.name),
            'value_score': snap.value_score,
            'confidence_level': snap.confidence_level,
            'title_count': title_count,
            'scores': {
                'availability': snap.availability_score,
                'exclusivity': snap.exclusivity_score,
                'quality': snap.quality_score,
                'price': snap.price_score,
                'accessibility': snap.accessibility_score,
            },
        })

    return {
        'snapshot_date': snapshot_date.isoformat(),
        'global_title_count': _global_title_count(),
        'axis_labels': AXIS_LABELS,
        'platforms': platforms,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_leaderboard(request):
    """
    Latest (or dated) platform benchmark snapshot for leaderboard UI.
    ?snapshot_date=YYYY-MM-DD  optional
    ?min_titles=1              hide platforms with no cached titles (default 1)
    """
    snapshot_date = _resolve_snapshot_date(request)
    min_titles = int(request.GET.get('min_titles', 1))
    payload = _snapshot_payload(snapshot_date, min_titles=min_titles)
    if not payload:
        return Response(
            {'detail': '벤치마크 스냅샷이 없습니다. run_benchmark_batch를 실행하세요.'},
            status=404,
        )
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_platform_detail(request, platform_id):
    """Single platform snapshot + genre distribution for pie/bar charts."""
    snapshot_date = _resolve_snapshot_date(request)
    if not snapshot_date:
        return Response({'detail': '벤치마크 스냅샷이 없습니다.'}, status=404)

    platform = Platform.objects.filter(pk=platform_id).first()
    if not platform:
        return Response({'detail': '플랫폼을 찾을 수 없습니다.'}, status=404)

    snap = PlatformBenchmarkSnapshot.objects.filter(
        platform=platform, snapshot_date=snapshot_date,
    ).first()
    if not snap:
        return Response({'detail': '해당 플랫폼 스냅샷이 없습니다.'}, status=404)

    avail = compute_availability_raw()
    genre_rows = (
        PlatformGenreStats.objects
        .filter(platform=platform, snapshot_date=snapshot_date)
        .order_by('-title_count')
    )
    genres = [
        {
            'genre_id': row.genre_id,
            'genre_name': GENRE_NAMES.get(row.genre_id, f'Genre {row.genre_id}'),
            'title_count': row.title_count,
        }
        for row in genre_rows
    ]

    return Response({
        'snapshot_date': snapshot_date.isoformat(),
        'platform_id': platform.id,
        'name': platform.name,
        'icon_url': _platform_icon(platform.name),
        'value_score': snap.value_score,
        'confidence_level': snap.confidence_level,
        'title_count': avail.get(platform.id, 0),
        'scores': {
            'availability': snap.availability_score,
            'exclusivity': snap.exclusivity_score,
            'quality': snap.quality_score,
            'price': snap.price_score,
            'accessibility': snap.accessibility_score,
        },
        'axis_labels': AXIS_LABELS,
        'genres': genres,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_genre_stats(request):
    """
    Genre distribution for one platform (pie chart data).
    ?platform_id= required
    ?snapshot_date= optional
    """
    platform_id = request.GET.get('platform_id')
    if not platform_id:
        return Response({'detail': 'platform_id가 필요합니다.'}, status=400)

    snapshot_date = _resolve_snapshot_date(request)
    if not snapshot_date:
        return Response({'detail': '벤치마크 스냅샷이 없습니다.'}, status=404)

    platform = Platform.objects.filter(pk=platform_id).first()
    if not platform:
        return Response({'detail': '플랫폼을 찾을 수 없습니다.'}, status=404)

    genre_rows = (
        PlatformGenreStats.objects
        .filter(platform=platform, snapshot_date=snapshot_date)
        .order_by('-title_count')
    )
    return Response({
        'snapshot_date': snapshot_date.isoformat(),
        'platform_id': platform.id,
        'platform_name': platform.name,
        'genres': [
            {
                'genre_id': row.genre_id,
                'genre_name': GENRE_NAMES.get(row.genre_id, f'Genre {row.genre_id}'),
                'title_count': row.title_count,
            }
            for row in genre_rows
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def benchmark_personal(request):
    """
    Personal Score leaderboard for the authenticated user.
    ?use_llm=1 (default) — run daily LLM taste analysis if not yet done today
    """
    from .personal_scoring import compute_personal_score

    use_llm = request.GET.get('use_llm', '1') != '0'
    payload = compute_personal_score(request.user, use_llm=use_llm)
    if not payload:
        return Response({'detail': '벤치마크 스냅샷이 없습니다.'}, status=404)
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_platform_page(request, platform_id):
    """Full platform benchmark detail page payload."""
    from .platform_benchmark import build_platform_page

    use_llm = request.GET.get('use_llm', '0') != '0'
    enrich_titles = request.GET.get('enrich_titles', '1') != '0'
    payload = build_platform_page(
        platform_id, request=request, use_llm=use_llm, enrich_titles=enrich_titles,
    )
    if not payload:
        return Response({'detail': '플랫폼 또는 스냅샷을 찾을 수 없습니다.'}, status=404)
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def benchmark_platform_insight(request, platform_id):
    """LLM insight only (cached monthly) — avoids full page rebuild."""
    from .platform_benchmark import _month_key, get_platform_llm_insight

    snapshot_date = _resolve_snapshot_date(request)
    if not snapshot_date:
        snapshot_date = (
            PlatformBenchmarkSnapshot.objects
            .order_by('-snapshot_date')
            .values_list('snapshot_date', flat=True)
            .first()
        )
    if not snapshot_date:
        return Response({'detail': '벤치마크 스냅샷이 없습니다.'}, status=404)

    platform = Platform.objects.filter(pk=platform_id).first()
    if not platform:
        return Response({'detail': '플랫폼을 찾을 수 없습니다.'}, status=404)

    snap = PlatformBenchmarkSnapshot.objects.filter(
        platform=platform, snapshot_date=snapshot_date,
    ).first()
    if not snap:
        return Response({'detail': '해당 플랫폼 스냅샷이 없습니다.'}, status=404)

    from .benchmark_scoring import compute_availability_raw
    from .models import PlatformGenreStats
    from .benchmark_constants import GENRE_NAMES

    avail = compute_availability_raw()
    title_count = avail.get(platform.id, 0)
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
    insight = get_platform_llm_insight(
        platform, snap, snapshot_date, use_llm=True,
        title_count=title_count, genres=genres,
    )
    return Response({
        'platform_id': platform.id,
        'llm_insight': insight,
        'llm_insight_month': _month_key(snapshot_date),
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def platform_user_reviews(request, platform_id):
    from .models import PlatformUserReview

    platform = Platform.objects.filter(pk=platform_id).first()
    if not platform:
        return Response({'detail': '플랫폼을 찾을 수 없습니다.'}, status=404)

    if request.method == 'GET':
        from .platform_benchmark import _reviews_payload
        return Response(_reviews_payload(platform, request))

    if not request.user.is_authenticated:
        return Response({'detail': '로그인이 필요합니다.'}, status=401)

    score = request.data.get('score')
    body = (request.data.get('body') or '').strip()
    try:
        score = int(score)
    except (TypeError, ValueError):
        return Response({'detail': '1-5 점수를 입력해주세요.'}, status=400)
    if score < 1 or score > 5:
        return Response({'detail': '1-5 점수를 입력해주세요.'}, status=400)

    review, _ = PlatformUserReview.objects.update_or_create(
        platform=platform,
        user=request.user,
        defaults={'score': score, 'body': body},
    )
    from .platform_benchmark import _reviews_payload, _user_review_payload
    block = _reviews_payload(platform, request)
    return Response({
        'review': _user_review_payload(review, request),
        **block,
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def platform_user_review_delete(request, platform_id):
    from .models import PlatformUserReview

    platform = Platform.objects.filter(pk=platform_id).first()
    if not platform:
        return Response({'detail': '플랫폼을 찾을 수 없습니다.'}, status=404)

    deleted, _ = PlatformUserReview.objects.filter(
        platform=platform, user=request.user,
    ).delete()
    if not deleted:
        return Response({'detail': '리뷰를 찾을 수 없습니다.'}, status=404)

    from .platform_benchmark import _reviews_payload
    return Response(_reviews_payload(platform, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def platform_user_review_reaction(request, platform_id, review_id):
    from .models import PlatformUserReview, PlatformUserReviewReaction
    from .platform_benchmark import _reviews_payload, _user_review_payload
    from .review_social import review_reaction_payload

    review = PlatformUserReview.objects.filter(
        pk=review_id, platform_id=platform_id,
    ).prefetch_related('reactions').first()
    if not review:
        return Response({'detail': '리뷰를 찾을 수 없습니다.'}, status=404)
    if review.user_id == request.user.id:
        return Response({'detail': '본인 리뷰에는 반응할 수 없습니다.'}, status=403)

    reaction = request.data.get('reaction')
    if reaction not in (PlatformUserReviewReaction.Reaction.LIKE, PlatformUserReviewReaction.Reaction.DISLIKE, None, ''):
        return Response({'detail': '올바른 반응 값이 아닙니다.'}, status=400)

    existing = PlatformUserReviewReaction.objects.filter(review=review, user=request.user).first()
    if not reaction:
        if existing:
            existing.delete()
    elif existing:
        if existing.reaction != reaction:
            existing.reaction = reaction
            existing.save(update_fields=['reaction', 'updated_at'])
    else:
        PlatformUserReviewReaction.objects.create(
            review=review, user=request.user, reaction=reaction,
        )

    review = PlatformUserReview.objects.filter(pk=review_id).prefetch_related('reactions', 'comments__author').first()
    platform = Platform.objects.filter(pk=platform_id).first()
    return Response({
        'review': _user_review_payload(review, request),
        'reactions': review_reaction_payload(review, request),
        **_reviews_payload(platform, request),
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def platform_user_review_comments(request, platform_id, review_id):
    from .models import PlatformUserReview, PlatformUserReviewComment
    from .platform_benchmark import _user_review_payload
    from .review_social import review_comment_payload

    review = PlatformUserReview.objects.filter(
        pk=review_id, platform_id=platform_id,
    ).select_related('user').first()
    if not review:
        return Response({'detail': '리뷰를 찾을 수 없습니다.'}, status=404)

    if request.method == 'GET':
        comments = review.comments.select_related('author').all()
        return Response({
            'comments': [review_comment_payload(item, request) for item in comments],
        })

    if not request.user.is_authenticated:
        return Response({'detail': '로그인이 필요합니다.'}, status=401)

    content = (request.data.get('content') or '').strip()
    if not content:
        return Response({'detail': '댓글 내용을 입력해주세요.'}, status=400)

    comment = PlatformUserReviewComment.objects.create(
        review=review, author=request.user, content=content,
    )
    review = PlatformUserReview.objects.filter(pk=review_id).prefetch_related('reactions', 'comments__author').first()
    return Response({
        'comment': review_comment_payload(comment, request),
        'review': _user_review_payload(review, request),
    }, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def platform_user_review_comment_delete(request, platform_id, comment_id):
    from .models import PlatformUserReviewComment
    from .platform_benchmark import _user_review_payload

    comment = PlatformUserReviewComment.objects.filter(
        pk=comment_id, review__platform_id=platform_id, author=request.user,
    ).select_related('review').first()
    if not comment:
        return Response({'detail': '댓글을 찾을 수 없습니다.'}, status=404)

    review_id = comment.review_id
    comment.delete()
    from .models import PlatformUserReview
    review = PlatformUserReview.objects.filter(pk=review_id).prefetch_related('reactions', 'comments__author').first()
    return Response({'review': _user_review_payload(review, request)})
