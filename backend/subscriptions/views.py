from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Platform, SubscriptionPlan, AddOnPass, Category
from .serializers import (
    CategorySerializer, PlatformSerializer, PlatformDetailSerializer,
    SubscriptionPlanSerializer, AddOnPassSerializer,
)


@api_view(['GET'])
def catalog(request):
    """Categories with nested platforms (for onboarding picker)."""
    categories = Category.objects.prefetch_related('platforms').order_by('name')
    data = []
    for cat in categories:
        platforms = cat.platforms.order_by('name')
        data.append({
            'id': cat.id,
            'name': cat.name,
            'platforms': PlatformSerializer(platforms, many=True).data,
        })
    return Response(data)


@api_view(['GET'])
def platform_list(request):
    """List all platforms with basic info. ?q= for name search."""
    platforms = Platform.objects.select_related('category').order_by('name')
    q = (request.GET.get('q') or '').strip()
    if q:
        platforms = platforms.filter(Q(name__icontains=q))
    serializer = PlatformSerializer(platforms, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def platform_detail(request, pk):
    """Single platform with nested plans and add-on passes."""
    platform = get_object_or_404(
        Platform.objects
        .select_related('category')
        .prefetch_related(
            'plans__bundle_contents__included_platform',
            'plans__requires_membership__platform',
            'addon_passes__pricings__base_plan__platform',
        ),
        pk=pk,
    )
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
    qs = SubscriptionPlan.objects.select_related('platform').prefetch_related(
        'bundle_contents__included_platform',
        'requires_membership__platform',
    ).order_by('platform__pk', 'price')

    platform_pk = request.GET.get('platform')
    billing = request.GET.get('billing')
    bundle = request.GET.get('bundle')

    if platform_pk:
        qs = qs.filter(platform__pk=platform_pk)
    if billing:
        qs = qs.filter(billing_period=billing)
    if bundle is not None:
        qs = qs.filter(is_bundle=(bundle.lower() == 'true'))

    serializer = SubscriptionPlanSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def bundle_list(request):
    """List all bundle plans with included platforms."""
    plans = (
        SubscriptionPlan.objects
        .filter(is_bundle=True)
        .select_related('platform')
        .prefetch_related('bundle_contents__included_platform')
        .order_by('price')
    )
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def addon_pass_list(request):
    """
    List add-on passes with tiered pricing.
    Query params:
      ?platform=<pk>  filter by platform
    """
    passes = AddOnPass.objects.select_related('platform').prefetch_related(
        'pricings__base_plan__platform',
    )
    platform_pk = request.GET.get('platform')
    if platform_pk:
        passes = passes.filter(platform__pk=platform_pk)

    serializer = AddOnPassSerializer(passes, many=True)
    return Response(serializer.data)
