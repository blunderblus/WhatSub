"""Django template pages for onboarding (same-origin OAuth + Gmail scan)."""
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from subscriptions.models import Platform, UserSubscription
from .forms import ManualSubscriptionForm
from .google_auth import conflicting_google_owner, google_link_status


def _page_context(request=None):
    backend = settings.BACKEND_URL.rstrip('/')
    gmail_scan_path = reverse('accounts:gmail_scan')
    gmail_scan_url = f'{backend}{gmail_scan_path}'
    # Gmail 읽기는 Google 로그인으로 해당 Google 계정 세션을 잡아야 합니다.
    # process=connect는 이미 다른 사용자에 연결된 Google 계정에서 실패합니다.
    google_auth_url = (
        f'{backend}{reverse("google_login")}'
        f'?next={quote(gmail_scan_url, safe="")}'
    )
    ctx = {
        'frontend_url': settings.FRONTEND_URL,
        'backend_url': backend,
        'gmail_scan_url': gmail_scan_url,
        'google_connect_url': google_auth_url,
        'google_auth_url': google_auth_url,
    }
    if request and request.user.is_authenticated:
        status = google_link_status(request.user)
        ctx['google_status'] = status
        ctx['google_connected'] = status == 'connected'
        other = conflicting_google_owner(request.user)
        ctx['google_conflict_user'] = other.username if other else ''
    return ctx


def login_redirect(request):
    """allauth LOGIN_URL — 프론트 로그인으로 보냄."""
    next_url = request.GET.get('next', settings.FRONTEND_URL + '/login')
    return redirect(next_url)


@login_required
def onboarding_page(request):
    return render(request, 'accounts/onboarding.html', _page_context(request))


@login_required
def gmail_scan_page(request):
    ctx = _page_context(request)
    if ctx.get('google_conflict_user'):
        messages.warning(
            request,
            f'이 Google 이메일은 이미 "{ctx["google_conflict_user"]}" 계정에 연결되어 있습니다. '
            'Gmail 스캔은 Google 로그인으로 해당 계정을 사용해야 합니다.',
        )
    return render(request, 'accounts/gmail_scan.html', ctx)


@login_required
def google_connect_page(request):
    """Google OAuth를 백엔드 URL로 시작 (redirect_uri 불일치 방지)."""
    return redirect(_page_context(request)['google_auth_url'])


@login_required
def onboarding_complete_page(request):
    return render(request, 'accounts/onboarding_complete.html', _page_context(request))


@login_required
def manual_add_page(request):
    if request.method == 'POST':
        form = ManualSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'{subscription.platform.name} 구독을 추가했습니다.')
            return redirect('accounts:onboarding_complete')
    else:
        form = ManualSubscriptionForm(initial={
            'start_date': timezone.now().date(),
            'payment_method': '',
        })

    return render(request, 'accounts/manual_add.html', {'form': form})


@login_required
@require_http_methods(['POST'])
def save_from_gmail_page(request):
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
        billing_cycle=request.POST.get('billing_cycle') or 'monthly',
        payment_method='Gmail 감지',
        start_date=today,
        renewal_date=request.POST.get('renewal_date') or today,
        memo='Gmail 받은편지함에서 자동 감지됨',
    )
    messages.success(request, f'{platform.name} 구독을 추가했습니다.')

    next_url = request.POST.get('next') or ''
    if next_url == 'complete':
        return redirect('accounts:onboarding_complete')
    return redirect('accounts:gmail_scan')
