from rest_framework import serializers
from .models import (
    Category, Platform, SubscriptionPlan, BundleContent,
    AddOnPass, AddOnPassPricing, UserSubscription,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class AddOnPassPricingSerializer(serializers.ModelSerializer):
    base_plan_name = serializers.SerializerMethodField()

    def get_base_plan_name(self, obj):
        if obj.base_plan:
            return f'{obj.base_plan.platform.name} - {obj.base_plan.plan_name}'
        return None

    class Meta:
        model = AddOnPassPricing
        fields = ['id', 'base_plan', 'base_plan_name', 'price', 'billing_period']


class AddOnPassSerializer(serializers.ModelSerializer):
    pricings = AddOnPassPricingSerializer(many=True, read_only=True)

    class Meta:
        model = AddOnPass
        fields = ['id', 'pass_name', 'pricings']


class BundleContentSerializer(serializers.ModelSerializer):
    included_platform_name = serializers.CharField(
        source='included_platform.name', read_only=True,
    )

    class Meta:
        model = BundleContent
        fields = ['id', 'included_platform', 'included_platform_name']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='platform.name', read_only=True)
    requires_membership_name = serializers.SerializerMethodField()
    bundle_contents = BundleContentSerializer(many=True, read_only=True)

    def get_requires_membership_name(self, obj):
        if obj.requires_membership:
            return f'{obj.requires_membership.platform.name} - {obj.requires_membership.plan_name}'
        return None

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'platform', 'platform_name', 'plan_name',
            'price', 'billing_period', 'max_streams', 'max_quality',
            'has_download', 'has_ads', 'requires_membership',
            'requires_membership_name', 'is_bundle', 'notes',
            'bundle_contents',
        ]


class PlatformSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Platform
        fields = [
            'id', 'name', 'category', 'category_name',
            'logo_url', 'website_url', 'country',
            'tmdb_provider_id', 'description',
        ]


class PlatformDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    plans = SubscriptionPlanSerializer(many=True, read_only=True)
    addon_passes = AddOnPassSerializer(many=True, read_only=True)

    class Meta:
        model = Platform
        fields = [
            'id', 'name', 'category', 'category_name',
            'logo_url', 'website_url', 'country',
            'tmdb_provider_id', 'description',
            'plans', 'addon_passes',
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    platform_name = serializers.CharField(source='platform.name', read_only=True)
    plan_detail = serializers.SerializerMethodField()

    def get_plan_detail(self, obj):
        if obj.plan:
            return {
                'id': obj.plan.id,
                'plan_name': obj.plan.plan_name,
                'price': obj.plan.price,
                'billing_period': obj.plan.billing_period,
                'max_quality': obj.plan.max_quality,
            }
        return None

    class Meta:
        model = UserSubscription
        fields = [
            'id', 'user', 'platform', 'platform_name', 'plan', 'plan_detail',
            'plan_name', 'payment_amount', 'billing_cycle', 'payment_method',
            'start_date', 'renewal_date', 'auto_renew', 'is_active',
            'memo', 'created_at',
        ]
