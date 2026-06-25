from django.db.models import Count, F, Q

from .models import CommunityComment, CommunityPost
from .serializers import BOARD_META


def normalize_board(board):
    return board if board in BOARD_META else CommunityPost.Board.OTT


def post_list_queryset(board, platform_id=None, flair_tag=None, no_flair=False, q=None, author=None):
    queryset = (
        CommunityPost.objects.filter(board=normalize_board(board))
        .select_related('author', 'author__preference_profile', 'platform')
        .prefetch_related('reactions', 'reports')
        .annotate(comment_count=Count('comments'))
        .order_by('-created_at')
    )
    if flair_tag == 'other':
        queryset = queryset.filter(flair_tag='other')
    elif platform_id:
        queryset = queryset.filter(platform_id=platform_id)
    elif no_flair:
        queryset = queryset.filter(platform_id__isnull=True, flair_tag='')
    if author is not None:
        queryset = queryset.filter(author=author)
    term = (q or '').strip()
    if term:
        queryset = queryset.filter(
            Q(title__icontains=term)
            | Q(content__icontains=term)
            | Q(author__nickname__icontains=term)
            | Q(author__username__icontains=term)
        )
    return queryset


def post_detail_queryset():
    return (
        CommunityPost.objects.select_related('author', 'author__preference_profile')
        .prefetch_related('reactions', 'reports', 'comments__reactions', 'comments__reports')
    )


def get_post_detail(pk):
    return post_detail_queryset().filter(pk=pk).first()


def increment_post_views(post):
    CommunityPost.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
    post.refresh_from_db()
    post.comment_count = post.comments.count()
    return post


def get_post(pk):
    return CommunityPost.objects.filter(pk=pk).first()


def get_comment(pk):
    return CommunityComment.objects.select_related('post').filter(pk=pk).first()


def get_user_comment(pk, user):
    return CommunityComment.objects.filter(pk=pk, author=user).first()


def get_comment_for_moderation(pk, user):
    comment = CommunityComment.objects.filter(pk=pk).first()
    if comment is None:
        return None
    from .permissions import can_manage_comment
    if not can_manage_comment(user, comment):
        return None
    return comment


def reload_post_with_comments(pk):
    post = post_detail_queryset().get(pk=pk)
    post.comment_count = post.comments.count()
    return post


def reload_post_reactions(pk):
    return CommunityPost.objects.prefetch_related('reactions').get(pk=pk)


def reload_post_reports(pk):
    return CommunityPost.objects.prefetch_related('reports').get(pk=pk)


def reload_comment_reactions(pk):
    return CommunityComment.objects.prefetch_related('reactions').get(pk=pk)


def reload_comment_reports(pk):
    return CommunityComment.objects.prefetch_related('reports').get(pk=pk)
