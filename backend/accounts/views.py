import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from subscriptions.models import SubscriptionPlan, UserSubscription
from subscriptions.platform_utils import resolve_official_platform
from .forms import ManualSubscriptionForm, SignUpForm

# Platform name -> local icon file under MEDIA_ROOT (subscriptions/media).
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


class AppLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # allauth adds extra auth backends, so login() needs an explicit one.
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, '가입을 환영합니다! 구독을 추가해 보세요.')
            return redirect('accounts:onboarding')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def onboarding(request):
    """Entry point: choose manual add or Gmail scan."""
    return render(request, 'accounts/onboarding.html')


@login_required
def manual_add(request):
    if request.method == 'POST':
        form = ManualSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'{subscription.platform.name} 구독을 추가했습니다.')
            return redirect('accounts:profile')
    else:
        form = ManualSubscriptionForm(initial={
            'start_date': timezone.now().date(),
            'payment_method': '',
        })

    return render(request, 'accounts/manual_add.html', {'form': form})


@login_required
def gmail_scan(request):
    """Render the Gmail-scan onboarding page (data fetched via detector AJAX)."""
    return render(request, 'accounts/gmail_scan.html')


def _resolve_platform(platform_id, platform_name):
    """Return (platform, is_official) for catalog entries only."""
    platform = resolve_official_platform(name=platform_name, platform_id=platform_id)
    return platform, platform is not None


def _create_user_subscription(user, item, source='gmail_onboarding'):
    """Persist one onboarding item. Official platforms only."""
    platform_id = item.get('platform_id')
    platform_name = (item.get('platform') or '').strip()
    plan_name = (item.get('plan_name') or '').strip() or '미정'
    billing_cycle = (item.get('billing_cycle') or 'monthly').lower()
    if billing_cycle not in ('monthly', 'annual', 'weekly'):
        billing_cycle = 'monthly'

    try:
        amount = int(item.get('payment_amount') or 0)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        raise ValueError('결제 금액은 필수입니다.')

    plan = None
    plan_id = item.get('plan_id')
    if plan_id:
        plan = SubscriptionPlan.objects.filter(pk=plan_id).first()

    platform, is_official = _resolve_platform(platform_id, platform_name)
    if not is_official or platform is None:
        label = platform_name or platform_id or '알 수 없음'
        raise ValueError(f'공식 지원 목록에 없는 서비스입니다: {label}')

    today = timezone.now().date()
    renewal = parse_date(item.get('renewal_date') or '') if item.get('renewal_date') else today

    if plan and not item.get('payment_amount'):
        amount = plan.price
        if not item.get('plan_name'):
            plan_name = plan.plan_name
        if plan.billing_period:
            billing_cycle = plan.billing_period

    sub = UserSubscription.objects.create(
        user=user,
        platform=platform,
        plan=plan,
        plan_name=plan_name,
        payment_amount=amount,
        billing_cycle=billing_cycle,
        payment_method='온보딩',
        start_date=today,
        renewal_date=renewal or today,
        memo='Gmail 온보딩' if source == 'gmail_onboarding' else '수동 온보딩',
    )
    return sub


@login_required
@require_http_methods(['POST'])
def onboarding_submit(request):
    """Batch-save selected subscriptions from the Gmail onboarding UI."""
    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    items = data.get('subscriptions') or []
    if not items:
        return JsonResponse({'error': '구독 항목이 없습니다.'}, status=400)

    created = 0
    errors = []
    for idx, item in enumerate(items):
        try:
            src = 'manual_onboarding' if item.get('source') == 'manual' else 'gmail_onboarding'
            _create_user_subscription(request.user, item, source=src)
            created += 1
        except ValueError as exc:
            errors.append({'index': idx, 'error': str(exc)})

    if created == 0:
        return JsonResponse({'error': errors[0]['error'] if errors else '저장 실패'}, status=400)

    return JsonResponse({
        'ok': True,
        'created': created,
        'errors': errors,
        'redirect': '/accounts/onboarding/complete/',
    })


@login_required
def onboarding_complete(request):
    """Welcome screen after onboarding (confetti + privacy note)."""
    return render(request, 'accounts/onboarding_complete.html')


@login_required
@require_http_methods(['POST'])
def save_from_gmail(request):
    """Legacy single-item save (kept for compatibility)."""
    try:
        item = {
            'platform': request.POST.get('platform'),
            'plan_name': request.POST.get('plan_name'),
            'payment_amount': request.POST.get('payment_amount'),
            'billing_cycle': request.POST.get('billing_cycle'),
            'renewal_date': request.POST.get('renewal_date'),
        }
        sub = _create_user_subscription(request.user, item)
        messages.success(request, f'{sub.platform.name} 구독을 추가했습니다.')
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('accounts:gmail_scan')
    return redirect('accounts:profile')


@login_required
def delete_subscription(request, pk):
    UserSubscription.objects.filter(pk=pk, user=request.user).delete()
    return redirect('accounts:profile')


@login_required
def profile_page(request):
    subscriptions = list(
        UserSubscription.objects
        .filter(user=request.user, is_active=True)
        .select_related('platform', 'plan')
        .order_by('renewal_date')
    )

    monthly_total = 0
    platform_ids = set()
    for sub in subscriptions:
        sub.icon_url = _platform_icon(sub.platform.name)
        platform_ids.add(sub.platform_id)
        if sub.billing_cycle == 'annual':
            monthly_total += round((sub.payment_amount or 0) / 12)
        elif sub.billing_cycle == 'weekly':
            monthly_total += round((sub.payment_amount or 0) * 52 / 12)
        else:
            monthly_total += sub.payment_amount or 0

    today = timezone.now().date()
    timeline = []
    for sub in subscriptions:
        if sub.renewal_date:
            timeline.append({
                'name': sub.platform.name,
                'days': (sub.renewal_date - today).days,
            })

    context = {
        'subscriptions': subscriptions,
        'subscription_count': len(subscriptions),
        'monthly_total': monthly_total,
        'platform_count': len(platform_ids),
        'timeline': sorted(timeline, key=lambda x: x['days']),
    }
    return render(request, 'accounts/profile.html', context)
