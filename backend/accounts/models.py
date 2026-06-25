from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models


class User(AbstractUser):
    nickname = models.CharField(max_length=30)
    profile_image = models.URLField(blank=True, null=True)
    bio = models.CharField(max_length=200, blank=True, default='')


class UserPreferenceProfile(models.Model):
    """Structured taste profile from onboarding chat + LLM parse."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preference_profile',
    )
    monthly_spend_cap = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Target monthly OTT spend cap in KRW',
    )
    preferred_genre_ids = models.JSONField(
        default=list, blank=True,
        help_text='TMDB genre IDs explicitly chosen by user',
    )
    consumption_habits = models.JSONField(
        default=dict, blank=True,
        help_text='e.g. binge, family, late_night, documentary_heavy',
    )
    platform_criteria = models.JSONField(
        default=list, blank=True,
        help_text='e.g. price, exclusives, quality, kids',
    )
    genre_weights = models.JSONField(
        default=dict, blank=True,
        help_text='LLM-parsed genre_id -> weight (0.0-1.0)',
    )
    taste_summary = models.TextField(blank=True)
    taste_title_habit = models.CharField(max_length=40, blank=True, default='')
    taste_title_genre = models.CharField(max_length=40, blank=True, default='')
    onboarding_chat_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'preferences:{self.user_id}'


class UserPreferenceChatSession(models.Model):
    """Optional onboarding chat transcript (skippable)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preference_chat_sessions',
    )
    messages = models.JSONField(
        default=list, blank=True,
        help_text='[{role: user|assistant, content: str}]',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'chat:{self.user_id}@{self.created_at:%Y-%m-%d}'


class UserTasteAnalysis(models.Model):
    """LLM taste analysis cache (up to 5 runs per user per calendar day)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='taste_analyses',
    )
    analysis_date = models.DateField(db_index=True)
    genre_weights = models.JSONField(default=dict, blank=True)
    llm_summary = models.TextField(blank=True)
    taste_title_habit = models.CharField(max_length=40, blank=True, default='')
    taste_title_genre = models.CharField(max_length=40, blank=True, default='')
    reaction_like_count = models.PositiveIntegerField(default=0)
    reaction_dislike_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-analysis_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'analysis_date']),
        ]

    def __str__(self):
        return f'taste:{self.user_id}@{self.analysis_date}'