from rest_framework import serializers

from .models import CommunityComment, CommunityPost, Reaction


BOARD_META = {
    CommunityPost.Board.NOTICE: {
        'key': CommunityPost.Board.NOTICE,
        'name': '공지사항',
        'description': '서비스 이용과 구독 관리에 필요한 안내를 확인하는 공간입니다.',
    },
    CommunityPost.Board.OTT: {
        'key': CommunityPost.Board.OTT,
        'name': 'OTT 게시판',
        'description': '구독료, 가성비, OTT별 추천 콘텐츠를 이야기하는 공간입니다.',
    },
    CommunityPost.Board.FREE: {
        'key': CommunityPost.Board.FREE,
        'name': '자유게시판',
        'description': '영화, 시리즈, 배우, 감상평 등 자유롭게 이야기하는 공간입니다.',
    },
}


def author_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'nickname': user.nickname or user.username,
        'profile_image': user.profile_image,
    }


def reaction_payload(obj, request):
    reactions = obj.reactions.all()
    like_count = sum(1 for item in reactions if item.reaction == Reaction.LIKE)
    dislike_count = sum(1 for item in reactions if item.reaction == Reaction.DISLIKE)
    my_reaction = None
    user = getattr(request, 'user', None)
    if getattr(user, 'is_authenticated', False):
        for item in reactions:
            if item.user_id == user.id:
                my_reaction = item.reaction
                break
    return {'like_count': like_count, 'dislike_count': dislike_count, 'my_reaction': my_reaction}


def report_payload(obj, request):
    reports = obj.reports.all()
    user = getattr(request, 'user', None)
    reported = False
    if getattr(user, 'is_authenticated', False):
        reported = any(item.user_id == user.id for item in reports)
    return {'report_count': len(reports), 'reported': reported}


class CommunityCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()

    class Meta:
        model = CommunityComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at', 'is_owner', 'reactions', 'reports']

    def get_author(self, obj):
        return author_payload(obj.author)

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.author_id == request.user.id)

    def get_reactions(self, obj):
        return reaction_payload(obj, self.context.get('request'))

    def get_reports(self, obj):
        return report_payload(obj, self.context.get('request'))


class CommunityPostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    board_label = serializers.SerializerMethodField()
    platform_name = serializers.SerializerMethodField()
    is_notice = serializers.SerializerMethodField()
    comment_count = serializers.IntegerField(read_only=True)
    is_owner = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    reports = serializers.SerializerMethodField()

    class Meta:
        model = CommunityPost
        fields = [
            'id', 'board', 'board_label', 'platform_id', 'platform_name', 'is_notice',
            'title', 'content', 'author',
            'view_count', 'comment_count', 'created_at', 'updated_at', 'is_owner', 'reactions', 'reports',
        ]

    def get_author(self, obj):
        return author_payload(obj.author)

    def get_board_label(self, obj):
        return BOARD_META.get(obj.board, {}).get('name', obj.board)

    def get_platform_name(self, obj):
        if obj.board == CommunityPost.Board.NOTICE:
            return None
        if obj.platform_id and getattr(obj, 'platform', None):
            return obj.platform.name
        return None

    def get_is_notice(self, obj):
        return obj.board == CommunityPost.Board.NOTICE

    def get_is_owner(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.author_id == request.user.id)

    def get_reactions(self, obj):
        return reaction_payload(obj, self.context.get('request'))

    def get_reports(self, obj):
        return report_payload(obj, self.context.get('request'))


class CommunityPostDetailSerializer(CommunityPostSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(CommunityPostSerializer.Meta):
        fields = CommunityPostSerializer.Meta.fields + ['comments']

    def get_comments(self, obj):
        return CommunityCommentSerializer(
            obj.comments.select_related('author').prefetch_related('reactions', 'reports'),
            many=True,
            context=self.context,
        ).data
