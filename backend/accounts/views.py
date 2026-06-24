from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.google_auth import user_has_google_token
from allauth.socialaccount.models import SocialToken

from subscriptions.models import Platform, SubscriptionPlan, UserSubscription
from subscriptions.serializers import UserSubscriptionSerializer
from .billing_dates import build_schedule_items, default_renewal_date, parse_subscription_date, subscription_period
from .forms import SignUpForm

_PLATFORM_LOGOS = {
    'netflix': 'Netflix_icon.png',
    'disney+': 'DisneyPlus_icon.png',
    'apple tv+': 'AppleTV_icon.png',
    'amazon prime video': 'AmazonPrimeVideo_icon.png',
    'coupang play': 'CoupangPlay_icon.png',
    'tving': 'TVING_icon.png',
    'wavve': 'Wavve_icon.png',
    'watcha': 'Watcha_icon.webp',
    'spotv': 'SpotvNow_icon.png',
}


def _platform_icon(name):
    filename = _PLATFORM_LOGOS.get((name or '').lower().strip())
    return f'{settings.MEDIA_URL}{filename}' if filename else ''


def _monthly_amount(subscription):
    amount = subscription.payment_amount or 0
    if subscription.billing_cycle == 'annual':
        return round(amount / 12)
    if subscription.billing_cycle == 'weekly':
        return round(amount * 52 / 12)
    return amount


def _is_bundle_subscription(subscription):
    if subscription.plan and subscription.plan.is_bundle:
        return True
    name = (subscription.platform.name or '').lower()
    return '번들' in name or 'bundle' in name


def _bundle_included_platforms(subscription):
    if not subscription.plan:
        return []
    return [
        {
            'platform_id': bc.included_platform_id,
            'platform_name': bc.included_platform.name,
            'icon_url': _platform_icon(bc.included_platform.name),
        }
        for bc in subscription.plan.bundle_contents.all()
    ]


def _subscription_payload(subscription, today=None):
    if today is None:
        today = timezone.now().date()
    data = UserSubscriptionSerializer(subscription).data
    data['icon_url'] = _platform_icon(subscription.platform.name)
    data['billing_cycle_label'] = subscription.get_billing_cycle_display()
    data['monthly_amount'] = _monthly_amount(subscription)
    data.update(subscription_period(subscription, today))
    data['is_bundle'] = _is_bundle_subscription(subscription)
    data['included_platforms'] = _bundle_included_platforms(subscription) if data['is_bundle'] else []
    return data


def _dashboard_payload(user):
    today = timezone.now().date()
    subscriptions = list(
        UserSubscription.objects
        .filter(user=user, is_active=True)
        .select_related('platform', 'plan')
        .prefetch_related('plan__bundle_contents__included_platform')
        .order_by('renewal_date')
    )
    monthly_total = sum(_monthly_amount(sub) for sub in subscriptions)
    platform_ids = {sub.platform_id for sub in subscriptions}
    timeline = [
        {
            'name': sub.platform.name,
            'date': sub.renewal_date,
            'days': (sub.renewal_date - today).days if sub.renewal_date else None,
        }
        for sub in subscriptions
        if sub.renewal_date
    ]

    calendar_events = []
    schedule_items = []
    for sub in subscriptions:
        period = subscription_period(sub, today)

        base = {
            'subscription_id': sub.id,
            'platform_id': sub.platform_id,
            'platform_name': sub.platform.name,
            'plan_name': sub.plan_name,
            'amount': sub.payment_amount,
            'start_date': sub.start_date.isoformat() if sub.start_date else None,
            'renewal_date': sub.renewal_date.isoformat() if sub.renewal_date else None,
        }
        calendar_events.append({
            'id': sub.id,
            **base,
            **period,
            'billing_cycle': sub.billing_cycle,
            'monthly_amount': _monthly_amount(sub),
            'icon_url': _platform_icon(sub.platform.name),
        })
        schedule_items.extend(build_schedule_items(sub, today))

    all_subscriptions = [_subscription_payload(sub, today) for sub in subscriptions]
    standalone_subscriptions = [s for s in all_subscriptions if not s['is_bundle']]
    bundle_subscriptions = [s for s in all_subscriptions if s['is_bundle']]

    return {
        'subscription_count': len(subscriptions),
        'monthly_total': monthly_total,
        'platform_count': len(platform_ids),
        'plan_count': SubscriptionPlan.objects.count(),
        'next_payment': timeline[0] if timeline else None,
        'timeline': sorted(timeline, key=lambda item: item['days']),
        'calendar_events': calendar_events,
        'schedule_items': schedule_items,
        'subscriptions': all_subscriptions,
        'standalone_subscriptions': standalone_subscriptions,
        'bundle_subscriptions': bundle_subscriptions,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token(request):
    return Response({'csrfToken': get_token(request)})


@api_view(['GET'])
@permission_classes([AllowAny])
def me(request):
    if not request.user.is_authenticated:
        return Response({'isAuthenticated': False})

    user = request.user
    has_gmail = user_has_google_token(user)
    return Response({
        'isAuthenticated': True,
        'hasGmailConnected': has_gmail,
        'user': {
            'id': user.id,
            'username': user.username,
            'nickname': user.nickname,
            'email': user.email,
            'profile_image': user.profile_image,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        },
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    nickname = (request.data.get('nickname') or '').strip()
    profile_image = (request.data.get('profile_image') or '').strip()

    if not nickname:
        return Response({'nickname': ['닉네임을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)
    if len(nickname) > 30:
        return Response({'nickname': ['닉네임은 30자 이하로 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)

    request.user.nickname = nickname
    request.user.profile_image = profile_image or None
    request.user.save(update_fields=['nickname', 'profile_image'])
    return Response({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'nickname': request.user.nickname,
            'email': request.user.email,
            'profile_image': request.user.profile_image,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
        },
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    if request.user.is_authenticated:
        return Response({'detail': 'Already authenticated'})

    form = SignUpForm(request.data)
    if not form.is_valid():
        return Response({'errors': form.errors}, status=status.HTTP_400_BAD_REQUEST)

    user = form.save()
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return Response({'detail': 'Signed up successfully'})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {'detail': '아이디 또는 비밀번호가 올바르지 않습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    login(request, user)
    return Response({'detail': 'Logged in successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'detail': 'Logged out successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    return Response(_dashboard_payload(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def renewal_notifications(request):
    """Upcoming subscription renewal alerts (default: next 14 days)."""
    today = timezone.now().date()
    try:
        days = int(request.GET.get('days', 14))
    except (TypeError, ValueError):
        days = 14
    days = max(1, min(days, 60))
    horizon = today + timedelta(days=days)

    subs = (
        UserSubscription.objects
        .filter(
            user=request.user,
            is_active=True,
            renewal_date__gte=today,
            renewal_date__lte=horizon,
        )
        .select_related('platform')
        .order_by('renewal_date')
    )
    notifications = [
        {
            'id': sub.id,
            'platform_name': sub.platform.name,
            'plan_name': sub.plan_name or (sub.plan.plan_name if sub.plan else ''),
            'renewal_date': sub.renewal_date.isoformat(),
            'days_until': (sub.renewal_date - today).days,
            'monthly_amount': _monthly_amount(sub),
            'icon_url': _platform_icon(sub.platform.name),
        }
        for sub in subs
    ]
    return Response({
        'today': today.isoformat(),
        'horizon_days': days,
        'notifications': notifications,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_feed(request):
    """Unified notifications: renewals, budget warnings, promos."""
    from accounts.models import UserPreferenceProfile

    today = timezone.now().date()
    try:
        horizon = int(request.GET.get('days', 14))
    except (TypeError, ValueError):
        horizon = 14
    horizon = max(1, min(horizon, 60))
    horizon_date = today + timedelta(days=horizon)

    items = []
    subs = (
        UserSubscription.objects
        .filter(
            user=request.user,
            is_active=True,
            renewal_date__gte=today,
            renewal_date__lte=horizon_date,
        )
        .select_related('platform')
        .order_by('renewal_date')
    )
    for sub in subs:
        days_until = (sub.renewal_date - today).days
        urgency = 'high' if days_until <= 3 else 'normal'
        items.append({
            'id': f'renewal-{sub.id}',
            'type': 'renewal',
            'urgency': urgency,
            'title': f'{sub.platform.name} 재결제 예정',
            'body': f'{sub.plan_name} · {sub.renewal_date.isoformat()} (D-{days_until})',
            'link': '/subscriptions',
            'created_at': today.isoformat(),
            'read': False,
        })

    pref = UserPreferenceProfile.objects.filter(user=request.user).first()
    cap = pref.monthly_spend_cap if pref else None
    if cap and cap > 0:
        monthly_total = sum(_monthly_amount(s) for s in UserSubscription.objects.filter(
            user=request.user, is_active=True,
        ))
        if monthly_total > cap:
            items.append({
                'id': 'budget-over',
                'type': 'budget',
                'urgency': 'high',
                'title': '월 OTT 예산 초과',
                'body': f'현재 구독 {monthly_total:,}원 / 예산 {cap:,}원',
                'link': '/benchmark?tab=personal',
                'created_at': today.isoformat(),
                'read': False,
            })
        elif monthly_total > cap * 0.85:
            items.append({
                'id': 'budget-warn',
                'type': 'budget',
                'urgency': 'normal',
                'title': '월 OTT 예산 임박',
                'body': f'현재 구독 {monthly_total:,}원 / 예산 {cap:,}원',
                'link': '/benchmark?tab=personal',
                'created_at': today.isoformat(),
                'read': False,
            })

    urgent = [n for n in items if n['urgency'] == 'high']
    return Response({
        'today': today.isoformat(),
        'notifications': items,
        'urgent': urgent,
        'unread_count': len(items),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_add(request):
    data = request.data.copy()
    platform_id = data.get('platform')
    plan_id = data.get('plan') or None

    try:
        platform = Platform.objects.get(pk=platform_id)
    except Platform.DoesNotExist:
        return Response({'platform': ['플랫폼을 선택해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)

    plan = None
    if plan_id:
        plan = SubscriptionPlan.objects.filter(pk=plan_id, platform=platform).first()
        if plan is None:
            return Response({'plan': ['선택한 플랫폼의 요금제가 아닙니다.']}, status=status.HTTP_400_BAD_REQUEST)

    if UserSubscription.objects.filter(user=request.user, platform=platform, is_active=True).exists():
        return Response(
            {'platform': ['이미 내 구독 목록에 있는 플랫폼입니다.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_dt = parse_subscription_date(data.get('start_date'), timezone.now().date())
    billing_cycle = data.get('billing_cycle') or (plan.billing_period if plan else 'monthly')
    renewal_dt = parse_subscription_date(
        data.get('renewal_date'),
        default_renewal_date(start_dt, billing_cycle),
    )
    plan_name = data.get('plan_name') or (plan.plan_name if plan else '미정')
    payment_method = data.get('payment_method') or ''

    try:
        payment_amount = int(data.get('payment_amount') or (plan.price if plan else 0))
    except (TypeError, ValueError):
        payment_amount = 0
    if payment_amount <= 0:
        return Response({'payment_amount': ['결제 금액을 입력해 주세요.']}, status=status.HTTP_400_BAD_REQUEST)

    subscription = UserSubscription.objects.create(
        user=request.user,
        platform=platform,
        plan=plan,
        plan_name=plan_name,
        payment_amount=payment_amount,
        billing_cycle=billing_cycle,
        payment_method=payment_method,
        start_date=start_dt,
        renewal_date=renewal_dt,
        auto_renew=bool(data.get('auto_renew', True)),
        memo=data.get('memo') or '',
    )
    return Response(_subscription_payload(subscription), status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_from_gmail(request):
    payload = _create_gmail_subscription(request.user, request.data)
    if not payload:
        return Response(
            {'platform': ['플랫폼을 입력해 주세요.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(payload, status=status.HTTP_201_CREATED)


def _create_gmail_subscription(user, data):
    platform_name = (data.get('platform') or '').strip()
    if not platform_name:
        return None

    plan_name = (data.get('plan_name') or '').strip() or '미정'
    amount = data.get('payment_amount')
    try:
        amount = int(float(amount)) if amount not in (None, '') else 0
    except (TypeError, ValueError):
        amount = 0

    platform, _ = Platform.objects.get_or_create(
        name__iexact=platform_name,
        defaults={'name': platform_name},
    )
    today = timezone.now().date()
    renewal = parse_subscription_date(data.get('renewal_date'), today)
    start = parse_subscription_date(data.get('start_date'), today)

    subscription = UserSubscription.objects.create(
        user=user,
        platform=platform,
        plan_name=plan_name,
        payment_amount=amount,
        billing_cycle=data.get('billing_cycle') or 'monthly',
        payment_method='Gmail 감지',
        start_date=start,
        renewal_date=renewal,
        memo='Gmail 받은편지함에서 자동 감지됨',
    )
    return _subscription_payload(subscription)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_bulk_from_gmail(request):
    items = request.data.get('subscriptions') or []
    if not isinstance(items, list) or not items:
        return Response(
            {'detail': '저장할 구독 항목이 없습니다.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    saved = []
    for item in items:
        if not item.get('selected', True):
            continue
        payload = _create_gmail_subscription(request.user, item)
        if payload:
            saved.append(payload)

    return Response({
        'saved_count': len(saved),
        'subscriptions': saved,
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_subscription(request, pk):
    deleted, _ = UserSubscription.objects.filter(pk=pk, user=request.user).delete()
    if not deleted:
        return Response({'detail': '구독을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)
