from django.conf import settings
from django.db import models

from subscriptions.models import Platform

class Content(models.Model):
    tmdb_id = models.IntegerField(unique=True)  # TMDB API id
    watchmode_id = models.IntegerField(null=True, blank=True, db_index=True)  # Watchmode title id

    title = models.CharField(max_length=255)  # 영문 제목
    korean_title = models.CharField(max_length=255, blank=True)  # 한국 제목
    overview = models.TextField(blank=True)  # 컨텐츠 정보

    poster_url = models.URLField(blank=True)  # 포스터 이미지 (작은거)
    backdrop_url = models.URLField(blank=True)  # 배경 이미지 (UIUX용)

    release_date = models.DateField(null=True)  # 개봉일

    rating = models.FloatField(default=0)  # 평점

    content_type = models.CharField(max_length=20)  # 영화, 드라마 등...

    sources_synced_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Last availability sync; used for 24h cache TTL',
    )
    sources_cache = models.JSONField(
        default=list, blank=True,
        help_text='Cached merged provider list (RapidAPI + Watchmode) for the frontend',
    )
    watchmode_checked = models.BooleanField(
        default=False,
        help_text='Whether a Watchmode lookup has been attempted for the current cache window',
    )

    def __str__(self):
        return self.korean_title or self.title


class ContentPlatform(models.Model):
    class SourceType(models.TextChoices):
        SUB = 'sub', 'Subscription'
        RENT = 'rent', 'Rent'
        BUY = 'buy', 'Buy'
        FREE = 'free', 'Free'

    content = models.ForeignKey(
        Content, on_delete=models.CASCADE, related_name='platform_sources',
    )  # Content Foreign key
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE,
    )  # subscriptions platform foreign key

    source_type = models.CharField(
        max_length=5, choices=SourceType.choices, default=SourceType.SUB,
    )  # 구독 / 대여 / 구매 / 무료
    price = models.PositiveIntegerField(
        null=True, blank=True, help_text='Rent/buy price (KRW)',
    )
    deeplink_url = models.URLField(blank=True)  # 스트리밍 서비스 해당 작품 가는 링크

    is_available = models.BooleanField(default=True)  # 현재 이용 가능 여부 True False
    updated_at = models.DateTimeField(auto_now=True)  # 마지막 업데이트 날짜

    class Meta:
        unique_together = ('content', 'platform', 'source_type')

    def __str__(self):
        return f'{self.content} @ {self.platform.name} ({self.source_type})'


class ContentReaction(models.Model):
    class Reaction(models.TextChoices):
        LIKE = 'like', 'Like'
        DISLIKE = 'dislike', 'Dislike'

    content = models.ForeignKey(
        Content, on_delete=models.CASCADE, related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='content_reactions',
    )
    reaction = models.CharField(max_length=7, choices=Reaction.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('content', 'user')

    def __str__(self):
        return f'{self.user} {self.reaction} {self.content}'


class WatchmodeUsage(models.Model):
    """Tracks Watchmode API call volume per month to stay within the free tier."""
    MONTHLY_LIMIT = 2400  # safety margin under the 2,500/month free tier

    month = models.CharField(max_length=7, unique=True)  # 'YYYY-MM'
    count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.month}: {self.count}'

    @staticmethod
    def _current_month():
        from django.utils import timezone
        return timezone.now().strftime('%Y-%m')

    @classmethod
    def can_call(cls):
        row = cls.objects.filter(month=cls._current_month()).first()
        return (row.count if row else 0) < cls.MONTHLY_LIMIT

    @classmethod
    def increment(cls, n=1):
        from django.db.models import F
        month = cls._current_month()
        row, _ = cls.objects.get_or_create(month=month)
        cls.objects.filter(pk=row.pk).update(count=F('count') + n)


class MediaType(models.TextChoices):
    MOVIE = 'movie', 'Movie'
    TV = 'tv', 'TV'


class StreamingCache(models.Model):
    """Per-title streaming availability for benchmark aggregation."""
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='streaming_cache_entries',
    )
    available = models.BooleanField(default=True)
    checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tmdb_id', 'media_type', 'platform')
        indexes = [
            models.Index(fields=['platform', 'available']),
            models.Index(fields=['tmdb_id', 'media_type']),
        ]

    def __str__(self):
        status = 'available' if self.available else 'unavailable'
        return f'{self.media_type}/{self.tmdb_id} @ {self.platform.name} ({status})'


class TitleMeta(models.Model):
    """TMDB metadata cache for benchmark scoring (separate from StreamingCache)."""
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    title = models.CharField(max_length=255, blank=True)
    poster_url = models.URLField(blank=True)
    vote_average = models.FloatField(default=0)
    vote_count = models.PositiveIntegerField(default=0)
    popularity = models.FloatField(default=0)

    class Meta:
        unique_together = ('tmdb_id', 'media_type')
        indexes = [
            models.Index(fields=['media_type', 'vote_average']),
        ]

    def __str__(self):
        return f'{self.media_type}/{self.tmdb_id} (★{self.vote_average})'


class TitleGenres(models.Model):
    """Genre membership per title (TMDB genre IDs as canonical taxonomy)."""
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    genre_id = models.PositiveIntegerField(db_index=True)

    class Meta:
        unique_together = ('tmdb_id', 'media_type', 'genre_id')
        indexes = [
            models.Index(fields=['genre_id']),
        ]

    def __str__(self):
        return f'{self.media_type}/{self.tmdb_id} genre={self.genre_id}'


class PlatformGenreStats(models.Model):
    """Aggregated genre distribution per platform (pie charts + Personal Score)."""
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='genre_stats',
    )
    genre_id = models.PositiveIntegerField(db_index=True)
    title_count = models.PositiveIntegerField(default=0)
    snapshot_date = models.DateField(db_index=True)

    class Meta:
        unique_together = ('platform', 'genre_id', 'snapshot_date')
        indexes = [
            models.Index(fields=['platform', 'snapshot_date']),
        ]

    def __str__(self):
        return f'{self.platform.name} genre={self.genre_id} ({self.title_count})'


class PlatformBenchmarkSnapshot(models.Model):
    """Final benchmark snapshot served to users (written by weekly batch)."""
    class ConfidenceLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='benchmark_snapshots',
    )
    snapshot_date = models.DateField(db_index=True)
    availability_score = models.FloatField(null=True, blank=True)
    exclusivity_score = models.FloatField(null=True, blank=True)
    quality_score = models.FloatField(null=True, blank=True)
    price_score = models.FloatField(null=True, blank=True)
    accessibility_score = models.FloatField(null=True, blank=True)
    confidence_level = models.CharField(
        max_length=10, choices=ConfidenceLevel.choices, default=ConfidenceLevel.LOW,
    )
    value_score = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('platform', 'snapshot_date')
        ordering = ['-snapshot_date', 'platform__name']

    def __str__(self):
        return f'{self.platform.name} @ {self.snapshot_date}'


class LLMJudgmentCache(models.Model):
    """Cached LLM judgments for exclusivity trending weight and price scoring."""
    class JudgmentType(models.TextChoices):
        EXCLUSIVITY_WEIGHT = 'exclusivity_weight', 'Exclusivity weight'
        PRICE_BENEFICIAL = 'price_beneficial', 'Price beneficial'
        USER_TASTE = 'user_taste', 'User taste analysis'
        ONBOARDING_PARSE = 'onboarding_parse', 'Onboarding preference parse'
        PLATFORM_INSIGHT = 'platform_insight', 'Platform benchmark insight'

    cache_key = models.CharField(max_length=255, unique=True)
    judgment_type = models.CharField(max_length=30, choices=JudgmentType.choices)
    target_id = models.CharField(
        max_length=64,
        help_text='tmdb_id or plan_id depending on judgment_type',
    )
    result_json = models.JSONField(default=dict)
    snapshot_date = models.DateField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['judgment_type', 'snapshot_date']),
        ]

    def __str__(self):
        return f'{self.judgment_type}:{self.target_id} ({self.snapshot_date})'


class PlatformUserReview(models.Model):
    """User score + opinion for a streaming platform (1-5)."""
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='user_reviews',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='platform_reviews',
    )
    score = models.PositiveSmallIntegerField(help_text='1-5 user rating')
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('platform', 'user')
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user_id} → {self.platform.name} ({self.score})'


class PlatformUserReviewReaction(models.Model):
    class Reaction(models.TextChoices):
        LIKE = 'like', 'Like'
        DISLIKE = 'dislike', 'Dislike'

    review = models.ForeignKey(
        PlatformUserReview, on_delete=models.CASCADE, related_name='reactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='platform_review_reactions',
    )
    reaction = models.CharField(max_length=10, choices=Reaction.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['review', 'user'], name='unique_platform_review_reaction'),
        ]


class PlatformUserReviewComment(models.Model):
    review = models.ForeignKey(
        PlatformUserReview, on_delete=models.CASCADE, related_name='comments',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='platform_review_comments',
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author_id}: {self.content[:30]}'
