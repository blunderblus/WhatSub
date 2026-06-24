"""Platform user review social features (Steam-style summaries, reactions)."""
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from community.models import CommunityPost, Reaction as CommunityReaction

from .models import PlatformUserReview, PlatformUserReviewReaction

SCORE_BUCKET_KEYS = ('very_positive', 'positive', 'mixed', 'negative', 'very_negative')
SCORE_TO_BUCKET = {
    5: 'very_positive',
    4: 'positive',
    3: 'mixed',
    2: 'negative',
    1: 'very_negative',
}
BUCKET_LABELS_KO = {
    'very_positive': '매우 긍정적',
    'positive': '긍정적',
    'mixed': '복합적',
    'negative': '부정적',
    'very_negative': '매우 부정적',
}


def empty_distribution():
    return {key: 0 for key in SCORE_BUCKET_KEYS}


def distribution_from_scores(scores):
    dist = empty_distribution()
    for score in scores:
        bucket = SCORE_TO_BUCKET.get(int(score))
        if bucket:
            dist[bucket] += 1
    return dist


def steam_verdict(dist, total):
    if total <= 0:
        return {'key': 'none', 'label': '평가 없음', 'positive_percent': 0}
    positive = dist['very_positive'] + dist['positive']
    pct = round(positive / total * 100)
    if pct >= 80:
        key = 'very_positive'
    elif pct >= 70:
        key = 'positive'
    elif pct >= 40:
        key = 'mixed'
    elif pct >= 20:
        key = 'negative'
    else:
        key = 'very_negative'
    return {'key': key, 'label': BUCKET_LABELS_KO[key], 'positive_percent': pct}


def build_score_summary(platform):
    all_scores = list(
        PlatformUserReview.objects.filter(platform=platform).values_list('score', flat=True),
    )
    recent_cutoff = timezone.now() - timedelta(days=30)
    recent_scores = list(
        PlatformUserReview.objects.filter(platform=platform, updated_at__gte=recent_cutoff)
        .values_list('score', flat=True),
    )
    all_dist = distribution_from_scores(all_scores)
    recent_dist = distribution_from_scores(recent_scores)
    all_total = len(all_scores)
    recent_total = len(recent_scores)
    return {
        'all': {
            'total': all_total,
            'distribution': all_dist,
            'distribution_labels': BUCKET_LABELS_KO,
            'verdict': steam_verdict(all_dist, all_total),
        },
        'recent': {
            'total': recent_total,
            'distribution': recent_dist,
            'distribution_labels': BUCKET_LABELS_KO,
            'verdict': steam_verdict(recent_dist, recent_total),
            'period_days': 30,
        },
    }


def review_reaction_payload(review, request):
    reactions = list(review.reactions.all())
    like_count = sum(1 for item in reactions if item.reaction == PlatformUserReviewReaction.Reaction.LIKE)
    dislike_count = sum(1 for item in reactions if item.reaction == PlatformUserReviewReaction.Reaction.DISLIKE)
    my_reaction = None
    user = getattr(request, 'user', None)
    if getattr(user, 'is_authenticated', False):
        for item in reactions:
            if item.user_id == user.id:
                my_reaction = item.reaction
                break
    return {
        'like_count': like_count,
        'dislike_count': dislike_count,
        'my_reaction': my_reaction,
        'score': like_count - dislike_count,
    }


def review_comment_payload(comment, request):
    from community.serializers import author_payload
    user = getattr(request, 'user', None)
    return {
        'id': comment.id,
        'author': author_payload(comment.author),
        'content': comment.content,
        'created_at': comment.created_at.isoformat(),
        'updated_at': comment.updated_at.isoformat(),
        'is_owner': bool(user and user.is_authenticated and comment.author_id == user.id),
    }


def community_board_preview(platform, request, limit=10):
    from community.serializers import CommunityPostSerializer

    notices = (
        CommunityPost.objects.filter(board=CommunityPost.Board.NOTICE)
        .select_related('author', 'platform')
        .annotate(comment_count=Count('comments'))
        .order_by('-created_at')[:3]
    )
    hot_posts = (
        CommunityPost.objects.filter(board=CommunityPost.Board.OTT, platform=platform)
        .select_related('author', 'platform')
        .prefetch_related('reactions')
        .annotate(
            comment_count=Count('comments', distinct=True),
            like_count=Count(
                'reactions',
                filter=Q(reactions__reaction=CommunityReaction.LIKE),
                distinct=True,
            ),
        )
        .order_by('-like_count', '-created_at')[:limit]
    )

    merged = []
    seen = set()
    for post in list(notices) + list(hot_posts):
        if post.id in seen:
            continue
        seen.add(post.id)
        merged.append(post)
        if len(merged) >= limit:
            break

    serializer = CommunityPostSerializer(merged, many=True, context={'request': request})
    return {
        'platform_board_url': f'/community?board=ott&platform_id={platform.id}',
        'platform_write_url': f'/community/write?board=ott&platform_id={platform.id}',
        'platform_name': platform.name,
        'threads': serializer.data,
    }
