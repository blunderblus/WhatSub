from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('platforms/', views.platform_list, name='platform_list'),
]