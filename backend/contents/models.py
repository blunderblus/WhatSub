from django.db import models
from django.conf import settings
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
