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
from .google_auth import conflicting_google_owner, clear_google_auth_intent, google_link_status, set_google_auth_intent
from .models import UserPreferenceProfile
from .onboarding_session import (
    ONBOARDING_METHOD_KEYS,
    clear_chat_resume,
    get_chat_resume,
    set_chat_resume,
    touch_method_pick,
)


ONBOARDING_METHODS = [
    {
        'key': 'gmail',
        'icon': '📨',
        'title': 'Gmail로 자동 찾기',
        'description': '받은편지함의 결제·구독 메일을 분석해 구독을 자동으로 찾아드립니다.',
    },
    {
        'key': 'receipt',
        'icon': '📷',
        'title': '결제내역·이미지 스캔',
        'description': '결제 내역이나 구독 화면 캡처를 AI로 분석해 구독 정보를 추출합니다.',
    },
    {
        'key': 'manual',
        'icon': '✍️',
        'title': '직접 추가하기',
        'description': '플랫폼과 플랜을 선택해 구독 정보를 직접 입력합니다.',
    },
]


def _get_methods_done(request):
    raw = request.session.get('onboarding_methods_done') or []
    return [key for key in raw if key in ONBOARDING_METHOD_KEYS]


def _mark_method_done(request, method):
    if method not in ONBOARDING_METHOD_KEYS:
        return
    done = _get_methods_done(request)
    if method in done:
        return
    done.append(method)
    request.session['onboarding_methods_done'] = done
    request.session.modified = True


def _onboarding_method_urls(frontend_url):
    gmail = reverse('accounts:gmail_scan')
    manual = reverse('accounts:manual_add')
    receipt_base = f'{frontend_url.rstrip("/")}/subscriptions/receipt-scan?onboarding=1'
    return {
        'gmail': f'{gmail}?method_index=0',
        'receipt': f'{receipt_base}&method_index=1',
        'manual': f'{manual}?method_index=2',
    }


def _onboarding_hub_url(saved=None):
    base = reverse('accounts:onboarding')
    if saved:
        return f'{base}?phase=subscribe_continue&saved={saved}'
    return base


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


def google_oauth_start(request):
    """Store login vs signup intent, then hand off to django-allauth Google OAuth."""
    intent = request.GET.get('intent', 'signup')
    set_google_auth_intent(request, intent)
    next_url = request.GET.get('next') or f'{settings.BACKEND_URL.rstrip("/")}{reverse("accounts:google_auth_done")}'
    return redirect(f'{reverse("google_login")}?next={quote(next_url, safe="")}')


def google_auth_done(request):
    """OAuth callback landing: send users to onboarding or the Vue app."""
    clear_google_auth_intent(request)
    if not request.user.is_authenticated:
        return redirect(f'{settings.FRONTEND_URL.rstrip("/")}/login?error=google')

    frontend = settings.FRONTEND_URL.rstrip('/')
    has_subscriptions = UserSubscription.objects.filter(
        user=request.user,
        is_active=True,
    ).exists()
    if has_subscriptions:
        return redirect(f'{frontend}/subscriptions')
    return redirect('accounts:onboarding')


def login_redirect(request):
    """allauth LOGIN_URL — 프론트 로그인으로 보냄."""
    next_url = request.GET.get('next', settings.FRONTEND_URL + '/login')
    return redirect(next_url)


@login_required
def onboarding_page(request):
    ctx = _page_context(request)
    subscription_count = UserSubscription.objects.filter(
        user=request.user,
        is_active=True,
    ).count()
    profile = UserPreferenceProfile.objects.filter(user=request.user).first()
    preferences_completed = bool(profile and profile.onboarding_chat_completed)

    saved = (request.GET.get('saved') or '').strip()
    if saved in ONBOARDING_METHOD_KEYS:
        _mark_method_done(request, saved)
    elif saved == 'preferences':
        pass

    methods_done = _get_methods_done(request)
    chat_phase = (request.GET.get('phase') or '').strip()

    if chat_phase == 'ott':
        set_chat_resume(
            request,
            step='ott',
            skipped_sub=request.GET.get('skipped_sub') == '1',
        )
    elif chat_phase == 'finish':
        clear_chat_resume(request)
    elif chat_phase == 'subscribe_continue' and saved in ONBOARDING_METHOD_KEYS:
        set_chat_resume(request, step='ask_more', saved_method=saved)
    elif chat_phase == 'subscribe':
        pass
    elif not chat_phase and not get_chat_resume(request) and not methods_done and subscription_count == 0:
        clear_chat_resume(request)

    chat_resume = get_chat_resume(request)

    method_urls = _onboarding_method_urls(settings.FRONTEND_URL)
    method_cards = []
    for method in ONBOARDING_METHODS:
        card = {**method, 'url': method_urls[method['key']], 'done': method['key'] in methods_done}
        method_cards.append(card)

    remaining_methods = [card for card in method_cards if not card['done']]
    all_methods_done = not remaining_methods and bool(methods_done)

    ctx.update({
        'subscription_count': subscription_count,
        'preferences_completed': preferences_completed,
        'saved_step': saved,
        'chat_phase': chat_phase,
        'skipped_sub': request.GET.get('skipped_sub') == '1',
        'methods_done': methods_done,
        'remaining_methods': remaining_methods,
        'all_methods_done': all_methods_done,
        'onboarding_url': reverse('accounts:onboarding'),
        'subscribe_return_url': f'{reverse("accounts:onboarding")}?phase=subscribe',
        'onboarding_complete_url': reverse('accounts:onboarding_complete'),
        'saved_replies': {
            'gmail': 'Gmail에서 구독을 저장했어요!',
            'receipt': '결제내역·이미지에서 구독을 찾아 저장했어요!',
            'manual': '구독을 직접 추가했어요!',
            'preferences': '취향 설정을 저장했어요!',
        },
        'method_success_labels': {
            'gmail': 'Gmail로 자동 찾기',
            'receipt': '결제내역·이미지 스캔',
            'manual': '직접 추가하기',
        },
        'nav_enter_message': {
            'ott': 'OTT 설문으로 이동하는 중…',
            'finish': '완료 화면으로 이동하는 중…',
            'subscribe_continue': '온보딩으로 돌아오는 중…',
            'subscribe': '온보딩으로 돌아가는 중…',
        }.get(chat_phase, ''),
        'chat_resume': chat_resume,
    })
    return render(request, 'accounts/onboarding.html', ctx)


@login_required
def gmail_scan_page(request):
    from subscriptions.models import Platform, SubscriptionPlan
    from subscriptions.serializers import PlatformSerializer, SubscriptionPlanSerializer

    method_index = request.GET.get('method_index', '0')
    touch_method_pick(request, 'gmail', method_index)

    ctx = _page_context(request)
    if ctx.get('google_conflict_user'):
        messages.warning(
            request,
            f'이 Google 이메일은 이미 "{ctx["google_conflict_user"]}" 계정에 연결되어 있습니다. '
            'Gmail 스캔은 Google 로그인으로 해당 계정을 사용해야 합니다.',
        )
    ctx['catalog_platforms'] = PlatformSerializer(
        Platform.objects.order_by('name'),
        many=True,
    ).data
    ctx['catalog_plans'] = SubscriptionPlanSerializer(
        SubscriptionPlan.objects.select_related('platform').order_by('platform__name', 'plan_name'),
        many=True,
    ).data
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
    method_index = request.GET.get('method_index', '2')
    touch_method_pick(request, 'manual', method_index)

    if request.method == 'POST':
        form = ManualSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.user = request.user
            subscription.save()
            messages.success(request, f'{subscription.platform.name} 구독을 추가했습니다.')
            return redirect(_onboarding_hub_url('manual'))
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
    if next_url == 'onboarding':
        return redirect(_onboarding_hub_url('gmail'))
    return redirect('accounts:gmail_scan')
