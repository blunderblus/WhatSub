from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from subscriptions.models import UserSubscription
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


@login_required
@require_http_methods(['POST'])
def save_from_gmail(request):
    """Create a UserSubscription from a detected Gmail subscription record."""
    from subscriptions.models import Platform

    platform_name = (request.POST.get('platform') or '').strip()
    plan_name = (request.POST.get('plan_name') or '').strip() or '미정'
    amount = request.POST.get('payment_amount') or 0
    try:
        amount = int(float(amount))
    except (TypeError, ValueError):
        amount = 0

    platform = Platform.objects.filter(name__iexact=platform_name).first()
    if not platform:
        platform = Platform.objects.create(name=platform_name or '기타')

    today = timezone.now().date()
    UserSubscription.objects.create(
        user=request.user,
        platform=platform,
        plan_name=plan_name,
        payment_amount=amount,
        billing_cycle='monthly',
        payment_method='Gmail 감지',
        start_date=today,
        renewal_date=today,
        memo='Gmail 받은편지함에서 자동 감지됨',
    )
    messages.success(request, f'{platform.name} 구독을 추가했습니다.')
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
