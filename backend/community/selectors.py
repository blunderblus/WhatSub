from django.db.models import Count, F

from .models import CommunityComment, CommunityPost
from .serializers import BOARD_META


def normalize_board(board):
    return board if board in BOARD_META else CommunityPost.Board.OTT


def post_list_queryset(board, platform_id=None, author=None):
    queryset = (
        CommunityPost.objects.filter(board=normalize_board(board))
        .select_related('author')
        .prefetch_related('reactions', 'reports')
        .annotate(comment_count=Count('comments'))
        .order_by('-created_at')
    )
    if platform_id:
        queryset = queryset.filter(platform_id=platform_id)
    if author is not None:
        queryset = queryset.filter(author=author)
    return queryset


def post_detail_queryset():
    return (
        CommunityPost.objects.select_related('author')
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
