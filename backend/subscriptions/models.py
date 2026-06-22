from django.db import models
from django.conf import settings


class BillingPeriod(models.TextChoices):
    WEEKLY = 'weekly', 'Weekly'
    MONTHLY = 'monthly', 'Monthly'
    ANNUAL = 'annual', 'Annual'


class MaxQuality(models.TextChoices):
    SD = 'SD', 'SD'
    HD = 'HD', 'HD'
    FHD = 'FHD', 'FHD'
    UHD = '4K', '4K'


class Category(models.Model):
    name = models.CharField(max_length=30)  # 구독 서비스의 유형 (e.g.스트리밍, 음악, 배달, 쇼핑...)

    def __str__(self):
        return self.name


class Platform(models.Model):
    class Country(models.TextChoices):
        KR = 'KR', 'Korea'
        GLOBAL = 'GLOBAL', 'Global'

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='platforms',
    )
    name = models.CharField(max_length=100)  # 서비스 이름 (e.g.아마존 프라임, 쿠팡 와우 멤버십)
    logo_url = models.URLField(blank=True)  # 구독 서비스 로고 이미지
    website_url = models.URLField(blank=True)  # 서비스 페이지 경로
    country = models.CharField(
        max_length=10, choices=Country.choices, default=Country.KR,
    )
    tmdb_provider_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='TMDB watch-provider id (Netflix=8, Disney+=337, ...)',
    )
    description = models.TextField(blank=True)  # 서비스 설명

    def __str__(self):
        return self.name


class SubscriptionPlan(models.Model):
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='plans',
    )
    plan_name = models.CharField(max_length=100)  # 일반, 와우, Basic, Standard, Premium
    price = models.PositiveIntegerField(default=0, help_text='KRW; 0 = free')
    billing_period = models.CharField(
        max_length=10, choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )
    max_streams = models.PositiveSmallIntegerField(default=1)
    max_quality = models.CharField(
        max_length=4, choices=MaxQuality.choices, default=MaxQuality.HD,
    )
    has_download = models.BooleanField(default=False)
    has_ads = models.BooleanField(default=False)
    requires_membership = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='dependent_plans',
        help_text='e.g. Coupang Play 와우 requires the Coupang WOW plan',
    )
    is_bundle = models.BooleanField(default=False)
    notes = models.TextField(
        blank=True, default='',
        help_text='App-store surcharge prices, affiliate discounts, download limits, etc.',
    )

    def __str__(self):
        return f'{self.platform.name} - {self.plan_name}'


class BundleContent(models.Model):
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.CASCADE, related_name='bundle_contents',
    )
    included_platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='included_in_bundles',
    )

    def __str__(self):
        return f'{self.plan} -> {self.included_platform.name}'


class AddOnPass(models.Model):
    platform = models.ForeignKey(
        Platform, on_delete=models.CASCADE, related_name='addon_passes',
    )
    pass_name = models.CharField(max_length=100)  # 스포츠 패스, J PLUS 패스, Paramount+ 패스

    def __str__(self):
        return f'{self.platform.name} - {self.pass_name}'


class AddOnPassPricing(models.Model):
    addon_pass = models.ForeignKey(
        AddOnPass, on_delete=models.CASCADE, related_name='pricings',
    )
    base_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.CASCADE,
        null=True, blank=True, related_name='addon_pricings',
        help_text='Base tier this price applies to; null = non-member price',
    )
    price = models.PositiveIntegerField(help_text='KRW')
    billing_period = models.CharField(
        max_length=10,
        choices=[
            (BillingPeriod.MONTHLY.value, 'Monthly'),
            (BillingPeriod.ANNUAL.value, 'Annual'),
        ],
        default=BillingPeriod.MONTHLY,
    )

    def __str__(self):
        return f'{self.addon_pass.pass_name} @ {self.price}'


class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # accounts User Foreign Key
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)  # subscriptions Platform Foreign Key
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='user_subscriptions',
    )

    plan_name = models.CharField(max_length=100)  # 현재 이용중인 구독 상품
    payment_amount = models.PositiveIntegerField()  # 지불 가격
    billing_cycle = models.CharField(
        max_length=10, choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )  # 유저 개인의 구독 단위
    payment_method = models.CharField(max_length=50)  # 지불 방식

    start_date = models.DateField()  # 시작일
    renewal_date = models.DateField()  # 결제 갱신일

    auto_renew = models.BooleanField(default=True)  # 자동 갱신 여부
    is_active = models.BooleanField(default=True)  # 현재 액티브한 구독인지 여부

    memo = models.TextField(blank=True)  # 유저가 기록할 수 있는 메모
    created_at = models.DateTimeField(auto_now_add=True)  # 필드 생성일

    def __str__(self):
        return f'{self.user} - {self.plan_name}'


class CustomPlatformSubmission(models.Model):
    """User-reported subscription platforms not yet in our official catalog."""
    class Source(models.TextChoices):
        GMAIL_ONBOARDING = 'gmail_onboarding', 'Gmail onboarding'
        MANUAL_ONBOARDING = 'manual_onboarding', 'Manual onboarding'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='custom_platform_submissions',
    )
    platform_name = models.CharField(max_length=100)
    plan_name = models.CharField(max_length=100, blank=True, default='')
    payment_amount = models.PositiveIntegerField()
    billing_cycle = models.CharField(max_length=10, choices=BillingPeriod.choices)
    renewal_date = models.DateField(null=True, blank=True)
    memo = models.TextField(blank=True, default='')
    source = models.CharField(
        max_length=30, choices=Source.choices, default=Source.GMAIL_ONBOARDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.platform_name} ({self.user})'
