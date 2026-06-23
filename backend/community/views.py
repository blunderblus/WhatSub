from django.db.models import Count, F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    CommunityComment,
    CommunityCommentReaction,
    CommunityCommentReport,
    CommunityPost,
    CommunityPostReaction,
    CommunityPostReport,
    Reaction,
)
from .serializers import BOARD_META, CommunityPostDetailSerializer, CommunityPostSerializer, reaction_payload, report_payload


@api_view(['GET'])
@permission_classes([AllowAny])
def boards(request):
    return Response({'boards': list(BOARD_META.values())})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def posts(request):
    if request.method == 'GET':
        board = request.GET.get('board') or CommunityPost.Board.OTT
        if board not in BOARD_META:
            board = CommunityPost.Board.OTT
        queryset = (
            CommunityPost.objects.filter(board=board)
            .select_related('author')
            .prefetch_related('reactions', 'reports')
            .annotate(comment_count=Count('comments'))
            .order_by('-created_at')
        )
        platform_id = request.GET.get('platform_id')
        if platform_id:
            queryset = queryset.filter(platform_id=platform_id)
        return Response({'board': BOARD_META[board], 'results': CommunityPostSerializer(queryset, many=True, context={'request': request}).data})

    if not request.user.is_authenticated:
        return Response({'detail': '로그인 후 글을 작성할 수 있습니다.'}, status=status.HTTP_401_UNAUTHORIZED)

    board = request.data.get('board')
    title = (request.data.get('title') or '').strip()
    content = (request.data.get('content') or '').strip()
    platform_id = request.data.get('platform_id')
    if board not in BOARD_META:
        return Response({'board': ['게시판을 선택해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    if board == CommunityPost.Board.NOTICE and not request.user.is_staff:
        return Response({'detail': '공지사항은 관리자만 작성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    if not title:
        return Response({'title': ['제목을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    if not content:
        return Response({'content': ['내용을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    post = CommunityPost.objects.create(
        board=board, title=title, content=content, author=request.user,
        platform_id=platform_id if platform_id else None,
    )
    post.comment_count = 0
    return Response(CommunityPostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def post_detail(request, pk):
    post = (
        CommunityPost.objects.select_related('author')
        .prefetch_related('reactions', 'reports', 'comments__reactions', 'comments__reports')
        .filter(pk=pk).first()
    )
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        CommunityPost.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
        post.refresh_from_db()
        post.comment_count = post.comments.count()
        return Response(CommunityPostDetailSerializer(post, context={'request': request}).data)
    if not request.user.is_authenticated or post.author_id != request.user.id:
        return Response({'detail': '작성자만 수정하거나 삭제할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'DELETE':
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    title = (request.data.get('title') or post.title).strip()
    content = (request.data.get('content') or post.content).strip()
    if not title or not content:
        return Response({'detail': '제목과 내용을 입력해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    post.title = title
    post.content = content
    post.save(update_fields=['title', 'content', 'updated_at'])
    post.comment_count = post.comments.count()
    return Response(CommunityPostDetailSerializer(post, context={'request': request}).data)


def _apply_reaction(model, lookup, user, reaction):
    existing = model.objects.filter(**lookup, user=user).first()
    if not reaction or (existing and existing.reaction == reaction):
        if existing:
            existing.delete()
    elif existing:
        existing.reaction = reaction
        existing.save(update_fields=['reaction', 'updated_at'])
    else:
        model.objects.create(**lookup, user=user, reaction=reaction)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_reaction(request, pk):
    post = CommunityPost.objects.filter(pk=pk).first()
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.author_id == request.user.id:
        return Response({'detail': 'Your own post cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    reaction = request.data.get('reaction')
    if reaction not in [Reaction.LIKE, Reaction.DISLIKE, None, '']:
        return Response({'detail': '올바른 반응 값이 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)
    _apply_reaction(CommunityPostReaction, {'post': post}, request.user, reaction)
    post = CommunityPost.objects.prefetch_related('reactions').get(pk=pk)
    return Response(reaction_payload(post, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_report(request, pk):
    post = CommunityPost.objects.filter(pk=pk).first()
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.author_id == request.user.id:
        return Response({'detail': 'Your own post cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    CommunityPostReport.objects.get_or_create(post=post, user=request.user)
    post = CommunityPost.objects.prefetch_related('reports').get(pk=pk)
    return Response(report_payload(post, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comments(request, pk):
    post = CommunityPost.objects.filter(pk=pk).first()
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': '공지사항에는 댓글을 작성할 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
    content = (request.data.get('content') or '').strip()
    if not content:
        return Response({'content': ['댓글 내용을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    CommunityComment.objects.create(post=post, author=request.user, content=content)
    post = CommunityPost.objects.select_related('author').prefetch_related('reactions', 'reports', 'comments__reactions', 'comments__reports').get(pk=pk)
    post.comment_count = post.comments.count()
    return Response(CommunityPostDetailSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_detail(request, pk):
    deleted, _ = CommunityComment.objects.filter(pk=pk, author=request.user).delete()
    if not deleted:
        return Response({'detail': '댓글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_reaction(request, pk):
    comment = CommunityComment.objects.select_related('post').filter(pk=pk).first()
    if comment is None:
        return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)
    if comment.post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': 'Notice comments cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    if comment.author_id == request.user.id:
        return Response({'detail': 'Your own comment cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    reaction = request.data.get('reaction')
    if reaction not in [Reaction.LIKE, Reaction.DISLIKE, None, '']:
        return Response({'detail': 'Invalid reaction value.'}, status=status.HTTP_400_BAD_REQUEST)
    _apply_reaction(CommunityCommentReaction, {'comment': comment}, request.user, reaction)
    comment = CommunityComment.objects.prefetch_related('reactions').get(pk=pk)
    return Response(reaction_payload(comment, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_report(request, pk):
    comment = CommunityComment.objects.select_related('post').filter(pk=pk).first()
    if comment is None:
        return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)
    if comment.post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': 'Notice comments cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    if comment.author_id == request.user.id:
        return Response({'detail': 'Your own comment cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    CommunityCommentReport.objects.get_or_create(comment=comment, user=request.user)
    comment = CommunityComment.objects.prefetch_related('reports').get(pk=pk)
    return Response(report_payload(comment, request))
