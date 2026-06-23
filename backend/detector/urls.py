from django.urls import path
from . import views

app_name = 'detector'

urlpatterns = [
    path('test/', views.test_view, name='test_view'),
    path('gmail_test/', views.gmail_test, name='gmail_test'),
    path('gmail_messages/', views.gmail_messages, name='gmail_messages'),
    path('gmail_detail/', views.gmail_detail, name='gmail_detail'),
    path('gmail_scan_stream/', views.gmail_scan_stream, name='gmail_scan_stream'),
]
