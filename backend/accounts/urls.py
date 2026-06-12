from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('csrf/', views.csrf_token, name='csrf'),
    path('me/', views.me, name='me'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('subscriptions/', views.manual_add, name='manual_add'),
    path('onboarding/gmail/save/', views.save_from_gmail, name='save_from_gmail'),
    path('subscriptions/<int:pk>/delete/', views.delete_subscription, name='delete_subscription'),
]
