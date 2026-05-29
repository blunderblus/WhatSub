from django.urls import path
from . import views

app_name = 'contents'
urlpatterns = [
    path('search/', views.search_page, name='search'),
    path('movies/', views.movie_list_page, name='movie_list'),
    path('movies/<int:tmdb_id>/', views.movie_detail_page, name='movie_detail'),
    path('shows/', views.show_list_page, name='show_list'),
    path('shows/<int:tmdb_id>/', views.show_detail_page, name='show_detail'),
    path('genres/', views.tmdb_genres, name='tmdb_genres'),
    path('show_genres/', views.tmdb_show_genres, name='tmdb_show_genres'),
    path('movie_list/', views.tmdb_movie_list, name='tmdb_movie_list'),
    path('show_list/', views.tmdb_show_list, name='tmdb_show_list'),
    path('movie_detail/<int:tmdb_id>/', views.tmdb_movie_detail, name='tmdb_movie_detail'),
    path('show_detail/<int:tmdb_id>/', views.tmdb_show_detail, name='tmdb_show_detail'),
    path('tmdb_search/', views.tmdb_search, name='tmdb_search'),
    path('streaming_info/', views.api_streaming_info, name='streaming_info'),
]
