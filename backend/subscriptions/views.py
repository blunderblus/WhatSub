from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .selectors import (
    addon_pass_queryset,
    addon_passes_for_platform,
    bundle_plan_queryset,
    bundle_plans_for_platform,
    category_catalog_queryset,
    plan_list_queryset,
    platform_catalog_queryset,
    platform_detail_queryset,
    platform_list_queryset,
    regular_plans_for_platform,
    related_bundle_plans_for_platform,
)
from .serializers import (
    AddOnPassSerializer,
    PlatformDetailSerializer,
    PlatformSerializer,
    SubscriptionPlanSerializer,
)


@api_view(['GET'])
def platform_catalog(request, pk):
    """Plans, bundles, add-on passes, and cross-platform bundles for a platform."""
    platform = get_object_or_404(platform_catalog_queryset(), pk=pk)

    return Response({
        'platform_id': platform.id,
        'platform_name': platform.name,
        'plans': SubscriptionPlanSerializer(regular_plans_for_platform(platform), many=True).data,
        'bundles': SubscriptionPlanSerializer(bundle_plans_for_platform(platform), many=True).data,
        'related_bundles': SubscriptionPlanSerializer(related_bundle_plans_for_platform(platform), many=True).data,
        'addon_passes': AddOnPassSerializer(addon_passes_for_platform(platform), many=True).data,
    })


@api_view(['GET'])
def catalog(request):
    """Categories with nested platforms (for onboarding picker)."""
    data = []
    for category in category_catalog_queryset():
        platforms = category.platforms.order_by('name')
        data.append({
            'id': category.id,
            'name': category.name,
            'platforms': PlatformSerializer(platforms, many=True).data,
        })
    return Response(data)


@api_view(['GET'])
def platform_list(request):
    """List all platforms with basic info. ?q= for name search."""
    platforms = platform_list_queryset((request.GET.get('q') or '').strip())
    serializer = PlatformSerializer(platforms, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def platform_detail(request, pk):
    """Single platform with nested plans and add-on passes."""
    platform = get_object_or_404(platform_detail_queryset(), pk=pk)
    serializer = PlatformDetailSerializer(platform)
    return Response(serializer.data)


@api_view(['GET'])
def plan_list(request):
    """
    List all subscription plans.
    Query params:
      ?platform=<pk>   filter by platform
      ?billing=monthly|annual|weekly
      ?bundle=true|false
    """
    plans = plan_list_queryset(
        platform_pk=request.GET.get('platform'),
        billing=request.GET.get('billing'),
        bundle=request.GET.get('bundle'),
    )
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def bundle_list(request):
    """List all bundle plans with included platforms."""
    plans = bundle_plan_queryset()
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def addon_pass_list(request):
    """
    List add-on passes with tiered pricing.
    Query params:
      ?platform=<pk>  filter by platform
    """
    passes = addon_pass_queryset(request.GET.get('platform'))
    serializer = AddOnPassSerializer(passes, many=True)
    return Response(serializer.data)
