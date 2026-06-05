from django.contrib import admin
from .models import Content, ContentPlatform


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'korean_title', 'content_type', 'rating', 'release_date')
    list_filter = ('content_type',)
    search_fields = ('title', 'korean_title', 'tmdb_id', 'watchmode_id')


@admin.register(ContentPlatform)
class ContentPlatformAdmin(admin.ModelAdmin):
    list_display = ('id', 'content', 'platform', 'source_type', 'price', 'is_available', 'updated_at')
    list_filter = ('source_type', 'is_available', 'platform')
    search_fields = ('content__title', 'platform__name')
