from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import ContentReaction
from .personal_scoring import invalidate_personal_score_cache


@receiver([post_save, post_delete], sender=ContentReaction)
def clear_personal_score_cache_on_reaction(sender, instance, **kwargs):
    invalidate_personal_score_cache(instance.user_id)
