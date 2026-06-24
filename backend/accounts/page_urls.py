from django.urls import path

from . import page_views

app_name = 'accounts'

urlpatterns = [
    path('login/', page_views.login_redirect, name='login'),
    path('auth/google/done/', page_views.google_auth_done, name='google_auth_done'),
    path('onboarding/', page_views.onboarding_page, name='onboarding'),
    path('onboarding/manual/', page_views.manual_add_page, name='manual_add'),
    path('onboarding/gmail/', page_views.gmail_scan_page, name='gmail_scan'),
    path('onboarding/gmail/connect/', page_views.google_connect_page, name='google_connect'),
    path('onboarding/complete/', page_views.onboarding_complete_page, name='onboarding_complete'),
    path('onboarding/gmail/save/', page_views.save_from_gmail_page, name='save_from_gmail'),
]
