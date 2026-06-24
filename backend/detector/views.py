"""
Gmail subscription detection pipeline.

  1. Inbox scan (newer_than:1m, paginated)
  2. Metadata collection (subject, sender, snippet) for every message
  3. Rule-based pre-filter (headers/snippet only — NOT body)
  4. Deduplication
  5. Full body parse for candidates only
  6. LLM extraction → final subscription list
"""
import base64
import json
import logging
import queue
import re
import threading

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse

from allauth.socialaccount.models import SocialApp, SocialToken
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.header import decode_header, make_header

from accounts.google_auth import google_link_status
from .llm import extract_subscriptions, is_configured as llm_configured
from subscriptions.detected_utils import enrich_detected_subscription

logger = logging.getLogger('detector.gmail')

GMAIL_QUERY = 'newer_than:1m'
MAX_INBOX_SCAN = 300
MAX_LLM_CANDIDATES = 80


def _log(msg, *args):
    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        logger.info(msg, *args)


def _clip(text, n=72):
    text = (text or '').replace('\n', ' ').strip()
    return text if len(text) <= n else text[: n - 1] + '…'


def _emit_progress(on_progress, *, step, percent, emoji, message, detail=''):
    if not on_progress:
        return
    on_progress({
        'step': step,
        'percent': min(99, max(0, int(percent))),
        'emoji': emoji,
        'message': message,
        'detail': detail or '',
    })


def _loop_progress(on_progress, *, step, start_pct, end_pct, current, total, emoji, message_tpl):
    if not on_progress or total <= 0:
        return
    tick = max(1, total // 12)
    if current == 0 or current >= total - 1 or current % tick == 0:
        span = end_pct - start_pct
        pct = start_pct + int(span * current / total)
        _emit_progress(
            on_progress,
            step=step,
            percent=pct,
            emoji=emoji,
            message=message_tpl.format(current=current + 1, total=total),
        )

# PROJECT_CONTEXT — known services
SERVICE_NAMES = [
    'Netflix', 'Disney', 'Spotify', 'Apple', 'Google', 'OpenAI', 'ChatGPT',
    'Coupang', 'Baemin', '배민', '쿠팡', 'Tving', '티빙', 'Wavve', 'Watcha',
    'YouTube', 'Amazon Prime', 'iCloud', 'iTunes', 'Google One', 'WOW',
]

# Payment / subscription signals (weak — need context)
PAYMENT_KEYWORDS = [
    'payment', 'purchase', 'membership', 'premium', 'subscription',
    'renewal', 'invoice', 'receipt', 'billing', 'charged',
    '결제', '구매', '구독', '멤버십', '정기결제', '영수증', '청구',
    '결제내역', '이용료', '갱신',
]

# PG / wallet — strong billing signal
PAYMENT_PROCESSORS = [
    'NHN KCP', 'KG Inicis', 'Toss Payments', 'KakaoPay', 'Naver Pay',
    '네이버페이', '카카오페이', '토스', 'inicis', 'kcp',
]

# Known billing senders
BILLING_SENDER_HINTS = [
    'apple.com', 'icloud.com', 'google.com', 'itunes.com', 'coupang.com', 'netflix.com',
    'spotify.com', 'disneyplus.com', 'openai.com', 'tving.com', 'wavve.com',
    'watcha.com', 'baemin.com', 'youtube.com', 'amazon.com',
]

# Receipt subjects reused for every message from the same sender (e.g. Apple).
GENERIC_RECEIPT_SUBJECTS = [
    'apple에서 발행한 영수증',
    'your receipt from apple',
    'receipt from apple',
    'google play 주문 영수증',
    'google play receipt',
]

# Obvious non-subscription noise
EXCLUDE_HINTS = [
    'newsletter', 'unsubscribe', '광고', '프로모션', '할인 쿠폰',
    '배송', 'shipping', 'delivery', 'tracking', '주문 확인', '배달',
]


def _build_gmail_service(user):
    if not user.is_authenticated:
        return None, 'login required'

    social_token = SocialToken.objects.filter(
        account__user=user,
        account__provider='google',
    ).first()
    if social_token is None:
        return None, 'social token not found'

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    if not client_id:
        app = SocialApp.objects.filter(provider='google').first()
        if app:
            client_id, client_secret = app.client_id, app.secret

    credentials = Credentials(
        token=social_token.token,
        refresh_token=social_token.token_secret or None,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=client_id or None,
        client_secret=client_secret or None,
        scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    )

    return build('gmail', 'v1', credentials=credentials), None


def _decode_header_value(raw_value):
    if not raw_value:
        return ''
    try:
        return str(make_header(decode_header(raw_value)))
    except Exception:
        return raw_value


def _strip_html(html):
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _extract_body(payload):
    body = ''
    mime = payload.get('mimeType', '')
    data = payload.get('body', {}).get('data')

    if data:
        chunk = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        body = _strip_html(chunk) if mime == 'text/html' else chunk

    for part in payload.get('parts', []):
        part_mime = part.get('mimeType', '')
        if part_mime.startswith('multipart/'):
            body += ' ' + _extract_body(part)
            continue
        if part_mime == 'text/plain':
            part_data = part.get('body', {}).get('data')
            if part_data:
                body += ' ' + base64.urlsafe_b64decode(part_data).decode('utf-8', errors='replace')
        elif part_mime == 'text/html' and not body.strip():
            part_data = part.get('body', {}).get('data')
            if part_data:
                html = base64.urlsafe_b64decode(part_data).decode('utf-8', errors='replace')
                body += ' ' + _strip_html(html)

    return re.sub(r'\s+', ' ', body).strip()


def _contains_any(text, keywords):
    lower = (text or '').lower()
    return any(kw.lower() in lower for kw in keywords)


def _passes_prefilter(subject, sender, snippet):
    """Pre-filter on metadata only. Body is NOT used here."""
    header = f'{subject} {sender}'
    preview = f'{header} {snippet}'

    if _contains_any(preview, EXCLUDE_HINTS):
        if not _contains_any(sender, BILLING_SENDER_HINTS):
            if not _contains_any(preview, SERVICE_NAMES + PAYMENT_PROCESSORS):
                return False, 'excluded:noise'

    if _contains_any(sender, BILLING_SENDER_HINTS):
        return True, 'billing_sender'

    if _contains_any(preview, SERVICE_NAMES):
        return True, 'service_name'

    if _contains_any(preview, PAYMENT_PROCESSORS):
        return True, 'payment_processor'

    has_payment = _contains_any(preview, PAYMENT_KEYWORDS)
    if has_payment:
        receipt_like = _contains_any(preview, [
            'receipt', 'invoice', '영수증', '청구서', '결제 내역', '결제내역',
            'subscription', 'renewal', 'membership', '구독', '정기결제', '갱신',
        ])
        if receipt_like or _contains_any(preview, SERVICE_NAMES + PAYMENT_PROCESSORS):
            return True, 'payment_context'

    return False, 'no_match'


def _normalize_key_part(text, max_len=120):
    return re.sub(r'\s+', ' ', (text or '').lower()).strip()[:max_len]


def _is_generic_receipt_subject(subject):
    lower = (subject or '').lower()
    return any(marker in lower for marker in GENERIC_RECEIPT_SUBJECTS)


def _candidate_dedupe_key(item):
    """
    Apple/Google-style receipts share one subject line across different products.
    For those, keep every message id. Otherwise dedupe on metadata fingerprint.
    """
    sender_key = re.sub(r'\s+', '', item.get('sender', '').lower())[:100]
    subject_key = _normalize_key_part(item.get('subject'), 120)
    sender = item.get('sender', '')

    if _contains_any(sender, BILLING_SENDER_HINTS) and _is_generic_receipt_subject(item.get('subject')):
        return ('generic_receipt', sender_key, item.get('id'))

    snippet_key = _normalize_key_part(item.get('snippet'), 160)
    date_key = _normalize_key_part(item.get('date'), 80)
    return ('fingerprint', sender_key, subject_key, date_key, snippet_key)


def _dedupe_candidates(candidates):
    seen = set()
    unique = []
    for item in candidates:
        key = _candidate_dedupe_key(item)
        if key in seen:
            _log(
                '  dedupe skip | %s | snippet=%s',
                _clip(item.get('subject')),
                _clip(item.get('snippet'), 48),
            )
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _dedupe_subscriptions(subs):
    seen = set()
    unique = []
    for sub in subs:
        platform = (sub.get('platform') or '').strip().lower()
        if not platform:
            continue
        key = (
            platform,
            (sub.get('plan_name') or '').strip().lower(),
            sub.get('payment_amount'),
            (sub.get('billing_cycle') or 'monthly').strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(sub)
    return unique


def _list_message_ids(service, max_messages=MAX_INBOX_SCAN):
    ids = []
    page_token = None
    while len(ids) < max_messages:
        batch = min(100, max_messages - len(ids))
        kwargs = {'userId': 'me', 'q': GMAIL_QUERY, 'maxResults': batch}
        if page_token:
            kwargs['pageToken'] = page_token
        results = service.users().messages().list(**kwargs).execute()
        for msg in results.get('messages', []):
            ids.append(msg['id'])
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return ids


def _fetch_metadata(service, msg_id):
    msg = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='metadata',
        metadataHeaders=['Subject', 'From', 'Date'],
    ).execute()

    subject = sender = date = ''
    for header in msg.get('payload', {}).get('headers', []):
        name = header.get('name', '')
        if name == 'Subject':
            subject = _decode_header_value(header.get('value', ''))
        elif name == 'From':
            sender = _decode_header_value(header.get('value', ''))
        elif name == 'Date':
            date = header.get('value', '')

    return {
        'id': msg_id,
        'subject': subject,
        'sender': sender,
        'date': date,
        'snippet': msg.get('snippet', ''),
    }


def _fetch_body(service, msg_id):
    msg = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='full',
    ).execute()
    return _extract_body(msg.get('payload', {}))


def run_gmail_pipeline(service, user_label='', on_progress=None):
    """
    Full pipeline. Returns dict with subscriptions and pipeline stats.
    """
    _log('── scan start %s query=%s max=%d ──', user_label or '', GMAIL_QUERY, MAX_INBOX_SCAN)
    _emit_progress(on_progress, step=1, percent=8, emoji='📬', message='받은편지함을 열고 있어요…')

    _log('[1/6] inbox list …')
    message_ids = _list_message_ids(service)
    scanned = len(message_ids)
    _log('[1/6] done — %d message id(s)', scanned)
    _emit_progress(
        on_progress,
        step=1,
        percent=18,
        emoji='📬',
        message=f'최근 1개월 메일 {scanned}통을 찾았어요',
    )

    _log('[2/6] metadata + pre-filter …')
    _emit_progress(on_progress, step=2, percent=22, emoji='🔍', message='구독·결제 메일을 골라내는 중…')
    candidates = []
    rejected = 0
    total_msgs = len(message_ids)
    for i, msg_id in enumerate(message_ids):
        try:
            meta = _fetch_metadata(service, msg_id)
        except Exception as exc:
            _log('  metadata FAIL id=%s err=%s', msg_id, exc)
            continue
        ok, reason = _passes_prefilter(meta['subject'], meta['sender'], meta['snippet'])
        if ok:
            candidates.append(meta)
            _log(
                '  ✓ [%s] %s | %s',
                reason,
                _clip(meta['subject']),
                _clip(meta['sender'], 48),
            )
        else:
            rejected += 1
        _loop_progress(
            on_progress,
            step=2,
            start_pct=22,
            end_pct=42,
            current=i,
            total=total_msgs,
            emoji='🔍',
            message_tpl='메일 확인 중… ({current}/{total})',
        )

    _log('[2/6] done — matched %d / rejected %d', len(candidates), rejected)
    _emit_progress(
        on_progress,
        step=2,
        percent=44,
        emoji='✅',
        message=f'후보 {len(candidates)}통 발견!',
        detail=f'전체 {scanned}통 중 {rejected}통은 제외됐어요',
    )

    before_dedupe = len(candidates)
    _emit_progress(on_progress, step=3, percent=46, emoji='🧹', message='겹치는 메일 정리 중…')
    candidates = _dedupe_candidates(candidates)
    prefiltered = len(candidates)
    if before_dedupe != prefiltered:
        _log('[3/6] dedupe emails %d → %d', before_dedupe, prefiltered)
    else:
        _log('[3/6] dedupe emails — %d (no duplicates)', prefiltered)
    _emit_progress(
        on_progress,
        step=3,
        percent=48,
        emoji='🧹',
        message=f'분석할 메일 {prefiltered}통 준비 완료',
    )

    llm_inputs = []
    if prefiltered > MAX_LLM_CANDIDATES:
        _log('[4/6] body parse — capping at %d of %d candidates', MAX_LLM_CANDIDATES, prefiltered)
    else:
        _log('[4/6] body parse — %d candidate(s)', prefiltered)

    body_targets = candidates[:MAX_LLM_CANDIDATES]
    body_total = len(body_targets)
    _emit_progress(on_progress, step=4, percent=50, emoji='📖', message='메일 본문을 읽고 있어요…')
    for i, meta in enumerate(body_targets):
        try:
            body = _fetch_body(service, meta['id'])
            body_len = len(body or '')
        except Exception as exc:
            _log('  body FAIL id=%s err=%s — fallback to snippet', meta['id'], exc)
            body = meta.get('snippet', '')
            body_len = len(body or '')
        else:
            _log('  body OK %d chars | %s', body_len, _clip(meta['subject']))
        llm_inputs.append({
            'subject': meta['subject'],
            'sender': meta['sender'],
            'body': body or meta.get('snippet', ''),
            'source_subject': meta['subject'],
        })
        _loop_progress(
            on_progress,
            step=4,
            start_pct=50,
            end_pct=68,
            current=i,
            total=body_total,
            emoji='📖',
            message_tpl='본문 읽는 중… ({current}/{total})',
        )
        if on_progress and body_total:
            _emit_progress(
                on_progress,
                step=4,
                percent=50 + int(18 * (i + 1) / body_total),
                emoji='📖',
                message='본문 읽는 중…',
                detail=_clip(meta['subject'], 56),
            )

    _log('[4/6] done — %d email(s) ready for LLM', len(llm_inputs))

    subscriptions = []
    llm_used = False
    if llm_inputs and llm_configured():
        from detector.ai_client import resolve_ai_model
        _log('[5/6] LLM extract … model=%s', resolve_ai_model())
        _emit_progress(on_progress, step=5, percent=72, emoji='🤖', message='AI가 구독 정보를 추출하는 중…')

        def llm_progress(current, total, subject):
            _emit_progress(
                on_progress,
                step=5,
                percent=72 + int(22 * current / max(total, 1)),
                emoji='🤖',
                message=f'AI 분석 중… ({current}/{total})',
                detail=_clip(subject, 56),
            )

        raw = extract_subscriptions(llm_inputs, on_progress=llm_progress)
        llm_used = True
        _log('[5/6] LLM returned %d raw subscription(s)', len(raw))
        _emit_progress(on_progress, step=6, percent=96, emoji='✨', message='찾은 구독을 정리하는 중…')
        for sub in raw:
            if sub.get('source_subject'):
                continue
            platform = (sub.get('platform') or '').lower()
            plan = (sub.get('plan_name') or '').lower()
            for email in llm_inputs:
                blob = f"{email['subject']} {email['sender']} {email.get('body', '')[:800]}".lower()
                if platform and platform in blob:
                    sub['source_subject'] = email['subject']
                    break
                if plan and len(plan) > 2 and plan in blob:
                    sub['source_subject'] = email['subject']
                    break
        before_sub_dedupe = len(raw)
        subscriptions = _dedupe_subscriptions(raw)
        _log('[6/6] dedupe subscriptions %d → %d', before_sub_dedupe, len(subscriptions))
        for sub in subscriptions:
            _log(
                '  → %s | %s | %s원 | %s',
                sub.get('platform', '?'),
                sub.get('plan_name') or '미정',
                sub.get('payment_amount') if sub.get('payment_amount') is not None else '?',
                sub.get('billing_cycle', 'monthly'),
            )
    elif not llm_configured():
        _log('[5/6] SKIP — LLM not configured (AI_API_KEY / AI_API_BASE)')
    else:
        _log('[5/6] SKIP — no candidates for LLM')

    _log(
        '── scan done: scanned=%d prefiltered=%d llm_in=%d out=%d ──',
        scanned, prefiltered, len(llm_inputs), len(subscriptions),
    )

    return {
        'subscriptions': subscriptions,
        'scanned': scanned,
        'prefiltered': prefiltered,
        'llm_candidates': len(llm_inputs),
        'llm_used': llm_used,
    }


def test_view(request):
    return JsonResponse({'message': 'hello'})


def gmail_test(request):
    token = SocialToken.objects.filter(account__user=request.user).first()
    if token is None:
        return JsonResponse({'error': 'token not found'})
    return JsonResponse({'token': token.token})


def gmail_messages(request):
    service, error = _build_gmail_service(request.user)
    if error:
        return JsonResponse({'error': error})
    results = service.users().messages().list(userId='me', maxResults=10).execute()
    return JsonResponse({'messages': results.get('messages', [])})


def _build_scan_response(result, user):
    subs = [enrich_detected_subscription(sub) for sub in result['subscriptions']]
    if subs:
        message = f'{len(subs)}개의 구독을 찾았습니다.'
    elif result['prefiltered']:
        message = (
            f'{result["prefiltered"]}건의 후보 메일을 분석했지만 '
            '구독 결제 정보를 추출하지 못했습니다.'
        )
    else:
        message = (
            f'최근 1개월 {result["scanned"]}건을 스캔했지만 '
            '구독·결제 관련 메일을 찾지 못했습니다.'
        )

    return {
        'subscriptions': subs,
        'pipeline': {
            'scanned': result['scanned'],
            'prefiltered': result['prefiltered'],
            'llm_candidates': result['llm_candidates'],
            'llm_used': result['llm_used'],
        },
        'google_status': google_link_status(user),
        'message': message,
    }


def _sse(event, payload):
    return f'event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n'


def gmail_scan_stream(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)

    if not llm_configured():
        return JsonResponse({
            'error': 'llm not configured',
            'google_status': google_link_status(request.user),
        })

    def event_stream():
        event_queue = queue.Queue()

        def on_progress(payload):
            event_queue.put(('progress', payload))

        def run_pipeline():
            try:
                service, error = _build_gmail_service(request.user)
                if error:
                    event_queue.put(('scan_error', {
                        'error': error,
                        'google_status': google_link_status(request.user),
                    }))
                    return

                event_queue.put(('progress', {
                    'step': 0,
                    'percent': 4,
                    'emoji': '🔌',
                    'message': 'Gmail에 연결했어요',
                    'detail': '',
                }))

                user_label = f'user={request.user.username}'
                result = run_gmail_pipeline(service, user_label=user_label, on_progress=on_progress)
                response = _build_scan_response(result, request.user)
                event_queue.put(('complete', response))
            except Exception as exc:
                logger.exception('Gmail pipeline failed')
                event_queue.put(('scan_error', {'error': f'Gmail API 오류: {exc}'}))
            finally:
                event_queue.put(('done', None))

        worker = threading.Thread(target=run_pipeline, daemon=True)
        worker.start()

        while True:
            kind, payload = event_queue.get()
            if kind == 'done':
                break
            yield _sse(kind, payload)

        worker.join(timeout=1)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def gmail_detail(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)

    service, error = _build_gmail_service(request.user)
    if error:
        return JsonResponse({
            'error': error,
            'google_status': google_link_status(request.user),
        })

    if not llm_configured():
        return JsonResponse({
            'error': 'llm not configured',
            'google_status': google_link_status(request.user),
        })

    try:
        user_label = f'user={request.user.username}'
        result = run_gmail_pipeline(service, user_label=user_label)
    except Exception as exc:
        logger.exception('Gmail pipeline failed')
        return JsonResponse({'error': f'Gmail API 오류: {exc}'})

    return JsonResponse(
        _build_scan_response(result, request.user),
        json_dumps_params={'ensure_ascii': False},
    )
