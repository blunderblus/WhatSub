from django.db.models import Q

from .models import AddOnPass, BundleContent, Category, Platform, SubscriptionPlan


def platform_catalog_queryset():
    return Platform.objects.select_related('category')


def regular_plans_for_platform(platform):
    return _plans_for_platform(platform).filter(is_bundle=False)


def bundle_plans_for_platform(platform):
    return _plans_for_platform(platform).filter(is_bundle=True)


def related_bundle_plans_for_platform(platform):
    related_bundle_ids = (
        BundleContent.objects
        .filter(included_platform=platform)
        .values_list('plan_id', flat=True)
        .distinct()
    )
    return (
        SubscriptionPlan.objects
        .filter(id__in=related_bundle_ids, is_bundle=True)
        .select_related('platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )


def addon_passes_for_platform(platform):
    return (
        AddOnPass.objects
        .filter(platform=platform)
        .prefetch_related('pricings__base_plan__platform')
        .order_by('pass_name')
    )


def category_catalog_queryset():
    return Category.objects.prefetch_related('platforms').order_by('name')


def platform_list_queryset(search_query=''):
    platforms = Platform.objects.select_related('category').order_by('name')
    if search_query:
        return platforms.filter(Q(name__icontains=search_query))
    return platforms


def platform_detail_queryset():
    return (
        Platform.objects
        .select_related('category')
        .prefetch_related(
            'plans__bundle_contents__included_platform',
            'plans__requires_membership__platform',
            'addon_passes__pricings__base_plan__platform',
        )
    )


def plan_list_queryset(platform_pk=None, billing=None, bundle=None):
    plans = (
        SubscriptionPlan.objects
        .select_related('platform')
        .prefetch_related(
            'bundle_contents__included_platform',
            'requires_membership__platform',
        )
        .order_by('platform__pk', 'price')
    )

    if platform_pk:
        plans = plans.filter(platform__pk=platform_pk)
    if billing:
        plans = plans.filter(billing_period=billing)
    if bundle is not None:
        plans = plans.filter(is_bundle=(bundle.lower() == 'true'))
    return plans


def bundle_plan_queryset():
    return (
        SubscriptionPlan.objects
        .filter(is_bundle=True)
        .select_related('platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )


def addon_pass_queryset(platform_pk=None):
    passes = (
        AddOnPass.objects
        .select_related('platform')
        .prefetch_related('pricings__base_plan__platform')
    )
    if platform_pk:
        return passes.filter(platform__pk=platform_pk)
    return passes


def _plans_for_platform(platform):
    return (
        SubscriptionPlan.objects
        .filter(platform=platform)
        .select_related('platform', 'requires_membership__platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )
