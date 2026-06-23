from django.contrib import admin

from .models import (
    Content,
    ContentPlatform,
    LLMJudgmentCache,
    PlatformBenchmarkSnapshot,
    PlatformGenreStats,
    StreamingCache,
    TitleGenres,
    TitleMeta,
)


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


@admin.register(StreamingCache)
class StreamingCacheAdmin(admin.ModelAdmin):
    list_display = ('tmdb_id', 'media_type', 'platform', 'available', 'checked_at')
    list_filter = ('media_type', 'available', 'platform')
    search_fields = ('tmdb_id',)


@admin.register(TitleMeta)
class TitleMetaAdmin(admin.ModelAdmin):
    list_display = ('tmdb_id', 'media_type', 'vote_average', 'vote_count', 'popularity')
    list_filter = ('media_type',)
    search_fields = ('tmdb_id',)


@admin.register(TitleGenres)
class TitleGenresAdmin(admin.ModelAdmin):
    list_display = ('tmdb_id', 'media_type', 'genre_id')
    list_filter = ('media_type',)
    search_fields = ('tmdb_id',)


@admin.register(PlatformGenreStats)
class PlatformGenreStatsAdmin(admin.ModelAdmin):
    list_display = ('platform', 'genre_id', 'title_count', 'snapshot_date')
    list_filter = ('snapshot_date', 'platform')
    search_fields = ('platform__name',)


@admin.register(PlatformBenchmarkSnapshot)
class PlatformBenchmarkSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'platform', 'snapshot_date', 'value_score', 'confidence_level',
        'availability_score', 'exclusivity_score', 'quality_score',
    )
    list_filter = ('snapshot_date', 'confidence_level', 'platform')


@admin.register(LLMJudgmentCache)
class LLMJudgmentCacheAdmin(admin.ModelAdmin):
    list_display = ('cache_key', 'judgment_type', 'target_id', 'snapshot_date')
    list_filter = ('judgment_type', 'snapshot_date')
    search_fields = ('cache_key', 'target_id')
