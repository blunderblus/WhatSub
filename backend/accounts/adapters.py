"""django-allauth adapters for WhatSub custom User fields."""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


def _default_nickname(data, user):
    name = (data.get('name') or data.get('given_name') or '').strip()
    if name:
        return name[:30]
    email = (data.get('email') or user.email or '').strip()
    if email and '@' in email:
        return email.split('@')[0][:30]
    username = (user.username or 'User').strip()
    return username[:30] or 'User'


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Fill required nickname and Google profile image on social signup."""

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.nickname:
            user.nickname = _default_nickname(data, user)
        picture = data.get('picture')
        if not user.profile_image and picture:
            user.profile_image = picture
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        extra = sociallogin.account.extra_data or {}
        updates = []
        if not user.nickname:
            user.nickname = _default_nickname(extra, user)
            updates.append('nickname')
        if not user.profile_image and extra.get('picture'):
            user.profile_image = extra['picture']
            updates.append('profile_image')
        if updates:
            user.save(update_fields=updates)
        return user
