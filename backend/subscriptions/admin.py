from django.contrib import admin
from .models import (
    Category, Platform, SubscriptionPlan, BundleContent,
    AddOnPass, AddOnPassPricing, UserSubscription, CustomPlatformSubmission,
)


class SubscriptionPlanInline(admin.TabularInline):
    model = SubscriptionPlan
    extra = 0


class AddOnPassPricingInline(admin.TabularInline):
    model = AddOnPassPricing
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'country', 'tmdb_provider_id')
    list_filter = ('country', 'category')
    search_fields = ('name',)
    inlines = [SubscriptionPlanInline]


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'platform', 'plan_name', 'price', 'billing_period',
        'max_quality', 'max_streams', 'has_ads', 'is_bundle', 'requires_membership',
    )
    list_filter = ('billing_period', 'max_quality', 'has_ads', 'is_bundle', 'platform')
    search_fields = ('plan_name', 'platform__name')


@admin.register(BundleContent)
class BundleContentAdmin(admin.ModelAdmin):
    list_display = ('id', 'plan', 'included_platform')
    search_fields = ('plan__plan_name', 'included_platform__name')


@admin.register(AddOnPass)
class AddOnPassAdmin(admin.ModelAdmin):
    list_display = ('id', 'platform', 'pass_name')
    list_filter = ('platform',)
    search_fields = ('pass_name', 'platform__name')
    inlines = [AddOnPassPricingInline]


@admin.register(AddOnPassPricing)
class AddOnPassPricingAdmin(admin.ModelAdmin):
    list_display = ('id', 'addon_pass', 'base_plan', 'price', 'billing_period')
    list_filter = ('billing_period',)
    search_fields = ('addon_pass__pass_name',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'platform', 'plan_name', 'payment_amount',
        'billing_cycle', 'renewal_date', 'is_active', 'auto_renew',
    )
    list_filter = ('is_active', 'auto_renew', 'billing_cycle', 'platform')
    search_fields = ('user__username', 'plan_name', 'platform__name')


@admin.register(CustomPlatformSubmission)
class CustomPlatformSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'platform_name', 'plan_name', 'payment_amount',
        'billing_cycle', 'source', 'created_at',
    )
    list_filter = ('source', 'billing_cycle')
    search_fields = ('platform_name', 'plan_name', 'user__username')
