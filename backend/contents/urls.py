from django.urls import path
from . import benchmark_views, views

app_name = 'contents'
urlpatterns = [
    path('genres/', views.tmdb_genres, name='tmdb_genres'),
    path('show_genres/', views.tmdb_show_genres, name='tmdb_show_genres'),
    path('movie_list/', views.tmdb_movie_list, name='tmdb_movie_list'),
    path('show_list/', views.tmdb_show_list, name='tmdb_show_list'),
    path('movie_detail/<int:tmdb_id>/', views.tmdb_movie_detail, name='tmdb_movie_detail'),
    path('show_detail/<int:tmdb_id>/', views.tmdb_show_detail, name='tmdb_show_detail'),
    path('tmdb_search/', views.tmdb_search, name='tmdb_search'),
    path('streaming_info/', views.api_streaming_info, name='streaming_info'),
    path('reaction/<int:tmdb_id>/', views.content_reaction, name='content_reaction'),
    path('benchmark/', benchmark_views.benchmark_leaderboard, name='benchmark_leaderboard'),
    path('benchmark/genres/', benchmark_views.benchmark_genre_stats, name='benchmark_genre_stats'),
    path('benchmark/platforms/<int:platform_id>/', benchmark_views.benchmark_platform_detail, name='benchmark_platform_detail'),
    path('benchmark/personal/', benchmark_views.benchmark_personal, name='benchmark_personal'),
    path('benchmark/platforms/<int:platform_id>/page/', benchmark_views.benchmark_platform_page, name='benchmark_platform_page'),
    path('benchmark/platforms/<int:platform_id>/insight/', benchmark_views.benchmark_platform_insight, name='benchmark_platform_insight'),
    path('benchmark/platforms/<int:platform_id>/reviews/', benchmark_views.platform_user_reviews, name='platform_user_reviews'),
    path('benchmark/platforms/<int:platform_id>/reviews/me/', benchmark_views.platform_user_review_delete, name='platform_user_review_delete'),
    path('streaming_platforms/', views.streaming_platforms_filter, name='streaming_platforms_filter'),
]
