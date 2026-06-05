from django.shortcuts import render
from django.utils import timezone

from subscriptions.models import Platform, SubscriptionPlan, UserSubscription


def index(request):
    today = timezone.now().date()
    subscriptions = []
    monthly_total = 0
    next_payment = None

    if request.user.is_authenticated:
        subscriptions = list(
            UserSubscription.objects
            .filter(user=request.user, is_active=True)
            .select_related('platform', 'plan')
            .order_by('renewal_date')[:5]
        )
        for subscription in subscriptions:
            amount = subscription.payment_amount or 0
            if subscription.billing_cycle == 'annual':
                monthly_total += round(amount / 12)
            elif subscription.billing_cycle == 'weekly':
                monthly_total += round(amount * 52 / 12)
            else:
                monthly_total += amount

        if subscriptions:
            next_subscription = subscriptions[0]
            next_payment = {
                'name': next_subscription.platform.name,
                'date': next_subscription.renewal_date,
                'days': (next_subscription.renewal_date - today).days,
            }

    context = {
        'subscriptions': subscriptions,
        'subscription_count': len(subscriptions),
        'monthly_total': monthly_total,
        'next_payment': next_payment,
        'platform_count': Platform.objects.count(),
        'plan_count': SubscriptionPlan.objects.count(),
        'featured_platforms': Platform.objects.filter(
            name__in=[
                'Netflix',
                'Disney+',
                'TVING',
                'Wavve',
                'Watcha',
                'Coupang Play',
                'Amazon Prime Video',
                'Apple TV+',
            ]
        ).order_by('pk'),
    }
    return render(request, 'index.html', context)
