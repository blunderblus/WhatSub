from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    CommunityCommentReaction,
    CommunityCommentReport,
    CommunityPost,
    CommunityPostReaction,
    CommunityPostReport,
    Reaction,
)
from .selectors import (
    get_comment,
    get_post,
    get_post_detail,
    increment_post_views,
    normalize_board,
    post_list_queryset,
    reload_comment_reactions,
    reload_comment_reports,
    reload_post_reactions,
    reload_post_reports,
    reload_post_with_comments,
    get_user_comment,
)
from .serializers import BOARD_META, CommunityPostDetailSerializer, CommunityPostSerializer, reaction_payload, report_payload
from .services import apply_reaction, create_comment, create_post, report_once, update_post


@api_view(['GET'])
@permission_classes([AllowAny])
def boards(request):
    return Response({'boards': list(BOARD_META.values())})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def posts(request):
    if request.method == 'GET':
        board = normalize_board(request.GET.get('board') or CommunityPost.Board.OTT)
        mine = request.GET.get('mine') in ('1', 'true', 'True')
        if mine and not request.user.is_authenticated:
            return Response({'detail': '로그인 후 내 글을 확인할 수 있습니다.'}, status=status.HTTP_401_UNAUTHORIZED)
        queryset = post_list_queryset(
            board,
            request.GET.get('platform_id'),
            author=request.user if mine else None,
        )
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
    post = create_post(
        board=board,
        title=title,
        content=content,
        author=request.user,
        platform_id=platform_id,
    )
    return Response(CommunityPostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([AllowAny])
def post_detail(request, pk):
    post = get_post_detail(pk)
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        increment_post_views(post)
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
    update_post(post, title=title, content=content)
    return Response(CommunityPostDetailSerializer(post, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_reaction(request, pk):
    post = get_post(pk)
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.author_id == request.user.id:
        return Response({'detail': 'Your own post cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    reaction = request.data.get('reaction')
    if reaction not in [Reaction.LIKE, Reaction.DISLIKE, None, '']:
        return Response({'detail': '올바른 반응 값이 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)
    apply_reaction(CommunityPostReaction, {'post': post}, request.user, reaction)
    post = reload_post_reactions(pk)
    return Response(reaction_payload(post, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_report(request, pk):
    post = get_post(pk)
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.author_id == request.user.id:
        return Response({'detail': 'Your own post cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    report_once(CommunityPostReport, {'post': post}, request.user)
    post = reload_post_reports(pk)
    return Response(report_payload(post, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comments(request, pk):
    post = get_post(pk)
    if post is None:
        return Response({'detail': '게시글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    if post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': '공지사항에는 댓글을 작성할 수 없습니다.'}, status=status.HTTP_403_FORBIDDEN)
    content = (request.data.get('content') or '').strip()
    if not content:
        return Response({'content': ['댓글 내용을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    create_comment(post=post, author=request.user, content=content)
    post = reload_post_with_comments(pk)
    return Response(CommunityPostDetailSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_detail(request, pk):
    comment = get_user_comment(pk, request.user)
    if comment is None:
        return Response({'detail': '댓글을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_reaction(request, pk):
    comment = get_comment(pk)
    if comment is None:
        return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)
    if comment.post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': 'Notice comments cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    if comment.author_id == request.user.id:
        return Response({'detail': 'Your own comment cannot be reacted to.'}, status=status.HTTP_403_FORBIDDEN)
    reaction = request.data.get('reaction')
    if reaction not in [Reaction.LIKE, Reaction.DISLIKE, None, '']:
        return Response({'detail': 'Invalid reaction value.'}, status=status.HTTP_400_BAD_REQUEST)
    apply_reaction(CommunityCommentReaction, {'comment': comment}, request.user, reaction)
    comment = reload_comment_reactions(pk)
    return Response(reaction_payload(comment, request))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_report(request, pk):
    comment = get_comment(pk)
    if comment is None:
        return Response({'detail': 'Comment not found.'}, status=status.HTTP_404_NOT_FOUND)
    if comment.post.board == CommunityPost.Board.NOTICE:
        return Response({'detail': 'Notice comments cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    if comment.author_id == request.user.id:
        return Response({'detail': 'Your own comment cannot be reported.'}, status=status.HTTP_403_FORBIDDEN)
    report_once(CommunityCommentReport, {'comment': comment}, request.user)
    comment = reload_comment_reports(pk)
    return Response(report_payload(comment, request))
