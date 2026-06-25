"""Helpers for Google OAuth / Gmail token lookup."""
from django.contrib.auth import get_user_model

from allauth.socialaccount.models import SocialAccount, SocialToken

GOOGLE_AUTH_INTENT_SESSION_KEY = 'google_auth_intent'
GOOGLE_AUTH_INTENT_LOGIN = 'login'
GOOGLE_AUTH_INTENT_SIGNUP = 'signup'


def get_google_auth_intent(request):
    intent = request.session.get(GOOGLE_AUTH_INTENT_SESSION_KEY, GOOGLE_AUTH_INTENT_SIGNUP)
    if intent not in (GOOGLE_AUTH_INTENT_LOGIN, GOOGLE_AUTH_INTENT_SIGNUP):
        return GOOGLE_AUTH_INTENT_SIGNUP
    return intent


def set_google_auth_intent(request, intent):
    if intent not in (GOOGLE_AUTH_INTENT_LOGIN, GOOGLE_AUTH_INTENT_SIGNUP):
        intent = GOOGLE_AUTH_INTENT_SIGNUP
    request.session[GOOGLE_AUTH_INTENT_SESSION_KEY] = intent
    request.session.modified = True


def clear_google_auth_intent(request):
    request.session.pop(GOOGLE_AUTH_INTENT_SESSION_KEY, None)


def social_login_matches_existing_user(sociallogin):
    """True when OAuth should sign in an existing WhatSub account instead of registering."""
    if sociallogin.is_existing:
        return True

    account = sociallogin.account
    if SocialAccount.objects.filter(provider=account.provider, uid=account.uid).exists():
        return True

    extra = account.extra_data or {}
    email = (extra.get('email') or getattr(sociallogin.user, 'email', None) or '').strip()
    if email and get_user_model().objects.filter(email__iexact=email).exists():
        return True
    return False


def user_has_google_token(user):
    if not user.is_authenticated:
        return False
    return SocialToken.objects.filter(
        account__user=user,
        account__provider='google',
    ).exists()


def google_link_status(user):
    """
    Return connection state for the current session user.

    - connected: this user has a Google token
    - linked_elsewhere: same Google account is tied to another local user
    - not_linked: no Google account on record for this user
    """
    if not user.is_authenticated:
        return 'anonymous'

    if user_has_google_token(user):
        return 'connected'

    if SocialAccount.objects.filter(user=user, provider='google').exists():
        return 'no_token'

    return 'not_linked'


def conflicting_google_owner(user):
    """If this user's email matches another user's Google account, return that user."""
    email = (user.email or '').strip().lower()
    if not email:
        return None

    account = (
        SocialAccount.objects
        .filter(provider='google', user__email__iexact=email)
        .exclude(user=user)
        .select_related('user')
        .first()
    )
    return account.user if account else None
