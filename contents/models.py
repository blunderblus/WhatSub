from django.db import models
from subscriptions.models import Platform

class Content(models.Model):
    tmdb_id = models.IntegerField(unique=True) # TMDB API id

    title = models.CharField(max_length=255) # 영문 제목
    korean_title = models.CharField(max_length=255, blank=True) #한국 제목
    overview = models.TextField(blank=True) # 컨텐츠 정보
 
    poster_url = models.URLField(blank=True) # 포스터 이미지 (작은거)
    backdrop_url = models.URLField(blank=True) # 배경 이미지 (UIUX용)

    release_date = models.DateField(null=True) # 개봉일

    rating = models.FloatField(default=0) # 평점

    content_type = models.CharField(max_length=20) # 영화, 드라마 등...

class ContentPlatform(models.Model):
    content = models.ForeignKey(Content, on_delete=models.CASCADE) # Content Foreign key
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE) # subscriptions platform foreign key

    deeplink_url = models.URLField(blank=True) # 스트리밍 서비스 해당 작품 가는 링크

    is_available = models.BooleanField(default=True) # 현재 이용 가능 여부 True False

    updated_at = models.DateTimeField(auto_now=True) # 마지막 업데이트 날짜