from django.db import models
from django.conf import settings

class Category(models.Model):
    name = models.CharField(max_length=30) # 구독 서비스의 유형 (e.g.스트리밍, 음악, 배달, 쇼핑...)

class Platform(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE) # Category Foreign Key

    name = models.CharField(max_length=100) # 서비스 이름 (e.g.아마존 프라임, 쿠팡 와우 멤버십)
    logo_url = models.URLField(blank=True) # 구독 서비스 로고 이미지

    official_url = models.URLField(blank=True) # 서비스 페이지 경로
    
    base_price = models.IntegerField() # 최저 가격
    billing_cycle = models.CharField(max_length=20) # 구독 단위(e.g.주, 월, 연)

    description = models.TextField(blank=True) # 서비스 설명

class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) # accounts User Foreign Key
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE) # subscriptions Platform Foreign Key

    plan_name = models.CharField(max_length=100) # 현재 이용중인 구독 상품
    
    payment_amount = models.IntegerField() # 지불 가격

    billing_cycle = models.CharField(max_length=20) # 유저 개인의 구독 단위
    payment_method = models.CharField(max_length=50) # 지불 방식(e.g.신한카드, 하나카드, 무통장입금 국민...)

    start_date = models.DateField() # 시작일
    renewal_date = models.DateField() # 결제 갱신일

    auto_renew = models.BooleanField(default=True) # 자동 갱신 여부
    is_active = models.BooleanField(default=True) # 현재 액티브한 구독인지 여부

    memo = models.TextField(blank=True) # 유저가 기록할 수 있는 메모

    created_at = models.DateTimeField(auto_now_add=True) # 필드 생성일