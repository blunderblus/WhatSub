from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.AppLoginView.as_view(), name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('onboarding/manual/', views.manual_add, name='manual_add'),
    path('onboarding/gmail/', views.gmail_scan, name='gmail_scan'),
    path('onboarding/gmail/save/', views.save_from_gmail, name='save_from_gmail'),
    path('onboarding/submit/', views.onboarding_submit, name='onboarding_submit'),
    path('onboarding/complete/', views.onboarding_complete, name='onboarding_complete'),
    path('subscriptions/<int:pk>/delete/', views.delete_subscription, name='delete_subscription'),
    path('profile/', views.profile_page, name='profile'),
]
