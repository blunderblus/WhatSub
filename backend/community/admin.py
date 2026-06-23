from django.contrib import admin

from .models import (
    CommunityComment,
    CommunityCommentReaction,
    CommunityCommentReport,
    CommunityPost,
    CommunityPostReaction,
    CommunityPostReport,
)


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'board', 'author', 'view_count', 'created_at')
    list_filter = ('board', 'created_at')
    search_fields = ('title', 'content', 'author__username', 'author__nickname')


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')
    search_fields = ('content', 'author__username', 'author__nickname')


@admin.register(CommunityPostReaction)
class CommunityPostReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'reaction', 'updated_at')
    list_filter = ('reaction', 'updated_at')
    search_fields = ('post__title', 'user__username', 'user__nickname')


@admin.register(CommunityCommentReaction)
class CommunityCommentReactionAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'reaction', 'updated_at')
    list_filter = ('reaction', 'updated_at')
    search_fields = ('comment__content', 'user__username', 'user__nickname')


@admin.register(CommunityPostReport)
class CommunityPostReportAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('post__title', 'user__username', 'user__nickname')


@admin.register(CommunityCommentReport)
class CommunityCommentReportAdmin(admin.ModelAdmin):
    list_display = ('comment', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('comment__content', 'user__username', 'user__nickname')
