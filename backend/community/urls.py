from django.urls import path

from . import views

app_name = 'community'

urlpatterns = [
    path('boards/', views.boards, name='boards'),
    path('posts/', views.posts, name='posts'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('posts/<int:pk>/reaction/', views.post_reaction, name='post_reaction'),
    path('posts/<int:pk>/report/', views.post_report, name='post_report'),
    path('posts/<int:pk>/comments/', views.comments, name='comments'),
    path('comments/<int:pk>/', views.comment_detail, name='comment_detail'),
    path('comments/<int:pk>/reaction/', views.comment_reaction, name='comment_reaction'),
    path('comments/<int:pk>/report/', views.comment_report, name='comment_report'),
]
