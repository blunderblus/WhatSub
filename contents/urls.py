from django.urls import path
from . import views

app_name = 'contents'
urlpatterns = [
    path('search/', views.search_page, name='search'),
    path('tmdb_search/', views.tmdb_search, name='tmdb_search'),
    path('streaming_info/', views.api_streaming_info, name='streaming_info'),
]