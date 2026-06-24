from django.urls import path
from . import preference_views, views

app_name = 'accounts_api'

urlpatterns = [
    path('csrf/', views.csrf_token, name='csrf'),
    path('me/', views.me, name='me'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('renewals/', views.renewal_notifications, name='renewal_notifications'),
    path('notifications/', views.notifications_feed, name='notifications_feed'),
    path('subscriptions/', views.manual_add, name='manual_add'),
    path('onboarding/gmail/save/', views.save_from_gmail, name='save_from_gmail'),
    path('onboarding/gmail/save-bulk/', views.save_bulk_from_gmail, name='save_bulk_from_gmail'),
    path('onboarding/resume/', views.set_onboarding_resume, name='onboarding_resume'),
    path('receipt/extract/', views.extract_receipt, name='extract_receipt'),
    path('subscriptions/<int:pk>/delete/', views.delete_subscription, name='delete_subscription'),
    path('preferences/questions/', preference_views.preference_questions, name='preference_questions'),
    path('preferences/', preference_views.preference_profile, name='preference_profile'),
    path('preferences/complete/', preference_views.preference_complete, name='preference_complete'),
]
