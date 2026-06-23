"""Helpers for Google OAuth / Gmail token lookup."""
from allauth.socialaccount.models import SocialAccount, SocialToken


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
