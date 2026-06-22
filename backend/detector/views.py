import base64
import html
import logging
import re
from datetime import timedelta
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from allauth.socialaccount.models import SocialApp, SocialToken

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from email.header import decode_header, make_header

logger = logging.getLogger('detector.gmail')

# Cap on how much body text we keep per email before handing it to the LLM.
_MAX_BODY_CHARS = 4000


def _pipeline_log(msg):
    """Write a pipeline debug line (shows in runserver terminal via LOGGING)."""
    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        logger.info(msg)


def _pipeline_logging_enabled():
    return getattr(settings, 'GMAIL_PIPELINE_LOG', True)

# Create your views here.


def _build_gmail_service(user):
    """
    Build an authenticated Gmail service for the user, including the refresh
    token / client credentials so short-lived access tokens auto-renew.
    Returns (service, error_message).
    """
    if not user.is_authenticated:
        return None, 'login required'

    social_token = SocialToken.objects.filter(account__user=user).first()
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

    service = build('gmail', 'v1', credentials=credentials)
    return service, None

def test_view(request):
    return JsonResponse({
        'message' : 'hello'
    })


def gmail_test(request):

    print(request.user)

    token = SocialToken.objects.filter(
        account__user=request.user
    ).first()

    print(token)

    if token is None:
        return JsonResponse({
            'error': 'token not found'
        })

    return JsonResponse({
        'token': token.token
    })

def gmail_messages(request):

    service, error = _build_gmail_service(request.user)
    if error:
        return JsonResponse({'error': error})

    results = service.users().messages().list(
        userId='me',
        maxResults=10
    ).execute()

    messages = results.get('messages', [])

    return JsonResponse({
        'messages': messages
    })


KEYWORDS = [
    'Netflix',
    'Amazon Prime',
    'YouTube',
    'Spotify',
    'OpenAI',
    'ChatGPT',
    'Apple',
    'iTunes',
    'Monthly',
    'Weekly',
    'Disney+',
    'Tving',
    '티빙',
    'Wavve',
    'Apple TV+',
    'Coupang Play',
    '배민',
    '쿠팡',
    '결제',
    '청구서',
    '카드',
    '구독',
    '주문',
    '멤버십',
    'Premium',
    'NHN',
    '영수증',
    'Invoice',
    'Receipt',
    'Payment',
    'Purchase',
    'Membership',
    'Subscription',
    'Renewal',
    'Payment',
]



# Terms too generic for the server-side search (they match almost everything
# and would crowd out real subscription mail). Kept out of the Gmail query, but
# still used for the per-email keyword label in the debug trace.
_QUERY_NOISE = {'apple', 'premium', 'monthly', 'weekly', '카드', '주문'}


def _build_gmail_query(before_date=None, window='newer_than:1m'):
    """Build a Gmail search query that OR's the keyword list server-side."""
    seen, terms = set(), []
    for kw in KEYWORDS:
        low = kw.lower()
        if low in _QUERY_NOISE or low in seen:
            continue
        seen.add(low)
        terms.append(f'"{kw}"' if (' ' in kw or '+' in kw) else kw)
    clause = f'({" OR ".join(terms)})'
    if before_date:
        return f'{window} before:{before_date.year}/{before_date.month}/{before_date.day} {clause}'
    return f'{window} {clause}'


def _scan_window_bounds():
    """Hard cap: only emails within the last 30 days."""
    end = timezone.now().date()
    start = end - timedelta(days=30)
    return start, end


def _parse_email_date(date_str):
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).date()
    except (TypeError, ValueError, OverflowError):
        return None


def _build_scan_meta(candidates, before_date=None):
    window_start, window_end = _scan_window_bounds()
    dates = [
        d for c in candidates
        if (d := _parse_email_date(c.get('date')))
    ]
    oldest = min(dates) if dates else None
    newest = max(dates) if dates else None
    can_scan_older = bool(oldest and oldest > window_start)
    return {
        'window_start': window_start.isoformat(),
        'window_end': window_end.isoformat(),
        'oldest_email_date': oldest.isoformat() if oldest else None,
        'newest_email_date': newest.isoformat() if newest else None,
        'emails_parsed': len(candidates),
        'can_scan_older': can_scan_older,
        'next_before': oldest.isoformat() if can_scan_older else None,
        'scan_before': before_date.isoformat() if before_date else None,
    }


def _decode(value):
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _b64url_decode(data):
    if not data:
        return ''
    try:
        return base64.urlsafe_b64decode(data.encode('utf-8')).decode('utf-8', 'replace')
    except Exception:
        return ''


def _html_to_text(raw):
    text = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw)
    text = re.sub(r'(?s)<[^>]+>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def _find_part_data(payload, target_mime):
    """Depth-first search for the body data of a given MIME type."""
    if payload.get('mimeType') == target_mime and payload.get('body', {}).get('data'):
        return payload['body']['data']
    for part in payload.get('parts', []):
        found = _find_part_data(part, target_mime)
        if found:
            return found
    return None


def _extract_body(payload):
    """
    Full message body as plain text.

    Extracts BOTH the text/plain and (stripped) text/html alternatives and
    returns whichever has more content. Receipts (e.g. Apple) often ship a
    near-empty text/plain stub while the real line items live only in the HTML
    part, so a strict plain-first preference loses the important data.
    """
    plain_raw = _find_part_data(payload, 'text/plain')
    html_raw = _find_part_data(payload, 'text/html')

    plain_text = _b64url_decode(plain_raw) if plain_raw else ''
    html_text = _html_to_text(_b64url_decode(html_raw)) if html_raw else ''

    if plain_text or html_text:
        # Prefer the richer alternative (more text = more signal for the LLM).
        return html_text if len(html_text) > len(plain_text) else plain_text

    # Single-part messages put data directly on the top-level body.
    if payload.get('body', {}).get('data'):
        raw = _b64url_decode(payload['body']['data'])
        mime = payload.get('mimeType', '')
        return _html_to_text(raw) if 'html' in mime else raw
    return ''


def _list_message_ids(service, query, max_results):
    """Page through Gmail search results up to ``max_results`` message IDs."""
    ids = []
    page_token = None
    page_num = 0
    while len(ids) < max_results:
        page_num += 1
        resp = service.users().messages().list(
            userId='me', q=query, pageToken=page_token,
            maxResults=min(100, max_results - len(ids)),
        ).execute()
        batch = resp.get('messages', [])
        ids.extend(m['id'] for m in batch)
        if _pipeline_logging_enabled():
            _pipeline_log(f'[gmail] list page {page_num}: +{len(batch)} id(s), total {len(ids)}')
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    return ids


def _subscription_signal_score(email):
    """
    Higher score → more likely a real subscription/receipt email.
    Used to sort candidates before the LLM cap so receipts are not dropped.
    """
    text = ' '.join([
        email.get('subject') or '',
        email.get('sender') or '',
        email.get('body') or '',
    ]).lower()
    score = 0
    for signal in (
        '영수증', 'receipt', 'invoice', '갱신', 'renewal', 'renew',
        '구독', 'subscription', 'membership', '멤버십', '정기결제',
    ):
        if signal in text:
            score += 4
    if '월간' in text or 'monthly' in text:
        score += 3
    if '₩' in text or re.search(r'\d{1,3}(,\d{3})+', text):
        score += 2
    if re.search(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일', text):
        score += 2
    for platform in (
        'prime video', 'icloud', 'netflix', 'tving', '티빙', 'wavve',
        'watcha', 'disney', 'spotify', 'youtube', 'coupang play', 'chatgpt',
    ):
        if platform in text:
            score += 3
    if 'no_reply@email.apple.com' in text or 'apple.com' in text:
        score += 2
    for noise in ('세일', '할인', '광고', 'promotion', 'newsletter'):
        if noise in text:
            score -= 2
    return score


def _prioritize_candidates(candidates):
    """Sort by subscription signal score (highest first)."""
    return sorted(candidates, key=_subscription_signal_score, reverse=True)


def _collect_candidate_emails(service, max_results=200, trace=None, before_date=None):
    """
    Return subscription-candidate emails (with full body) found via a Gmail
    server-side keyword search. ``before_date`` narrows to older mail (Case A).
    """
    query = _build_gmail_query(before_date=before_date)
    if _pipeline_logging_enabled():
        preview = query if len(query) <= 120 else query[:117] + '...'
        _pipeline_log(f'[gmail] search query: {preview}')

    message_ids = _list_message_ids(service, query, max_results)

    if _pipeline_logging_enabled():
        _pipeline_log(f'[gmail] query matched {len(message_ids)} message(s) (cap {max_results})')

    candidates = []
    for idx, message_id in enumerate(message_ids, 1):
        msg = service.users().messages().get(userId='me', id=message_id).execute()
        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        subject = sender = date = ''
        for header in headers:
            name = header.get('name')
            if name == 'Subject':
                subject = _decode(header['value'])
            elif name == 'From':
                sender = _decode(header['value'])
            elif name == 'Date':
                date = header['value']

        snippet = msg.get('snippet', '')
        body = _extract_body(payload) or snippet

        # These all matched the Gmail search already (possibly in the body); the
        # label is only for the debug trace / console.
        combined_text = f'{subject} {sender} {snippet} {body}'.lower()
        matched = next((kw for kw in KEYWORDS if kw.lower() in combined_text), '(gmail)')

        if _pipeline_logging_enabled():
            _pipeline_log(
                f'[gmail] [{idx}/{len(message_ids)}] MATCH | kw={matched} '
                f'| body={len(body)}ch | {subject[:55]} | {sender[:35]}'
            )

        if trace is not None:
            trace.append({
                'subject': subject,
                'sender': sender,
                'date': date,
                'passed': True,
                'matched_keyword': matched,
                'body_chars': len(body),
            })

        candidates.append({
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': snippet,
            'body': body[:_MAX_BODY_CHARS],
        })

    if _pipeline_logging_enabled():
        _pipeline_log(f'[gmail] {len(candidates)} candidate(s) collected → ready for LLM')

    return candidates


def gmail_detail(request):
    """Rule-based listing of subscription-candidate emails."""
    if _pipeline_logging_enabled():
        _pipeline_log(f'[gmail] gmail_detail start user={request.user}')

    service, error = _build_gmail_service(request.user)
    if error:
        if _pipeline_logging_enabled():
            _pipeline_log(f'[gmail] gmail_detail aborted: {error}')
        return JsonResponse({'error': error})

    try:
        emails = _collect_candidate_emails(service)
    except Exception as exc:  # noqa: BLE001 - always answer JSON
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'scan failed: {exc}'}, status=500)

    if _pipeline_logging_enabled():
        _pipeline_log(f'[gmail] gmail_detail done: {len(emails)} email(s)')

    return JsonResponse({'emails': emails}, json_dumps_params={'ensure_ascii': False})


def gmail_analyze(request):
    """LLM-extracted, de-duplicated subscriptions from the inbox."""
    from . import llm

    if _pipeline_logging_enabled():
        _pipeline_log(f'[gmail] gmail_analyze start user={request.user} debug={request.GET.get("debug")}')

    service, error = _build_gmail_service(request.user)
    if error:
        if _pipeline_logging_enabled():
            _pipeline_log(f'[gmail] gmail_analyze aborted: {error}')
        return JsonResponse({'error': error})

    if not llm.is_configured():
        if _pipeline_logging_enabled():
            _pipeline_log('[gmail] gmail_analyze aborted: llm not configured')
        return JsonResponse({'error': 'llm not configured'})

    debug = request.GET.get('debug') in ('1', 'true', 'yes')
    trace = [] if debug else None
    before_date = parse_date(request.GET.get('before') or '')

    try:
        candidates = _collect_candidate_emails(service, trace=trace, before_date=before_date)
        scan_meta = _build_scan_meta(candidates, before_date=before_date)
        prioritized = _prioritize_candidates(candidates)
        llm_cap = 20 * 4  # keep in sync with llm._MAX_EMAILS_PER_BATCH * _MAX_LLM_BATCHES
        sent_count = min(len(prioritized), llm_cap)
        skipped = max(0, len(prioritized) - sent_count)

        if _pipeline_logging_enabled():
            _pipeline_log(
                f'[gmail] {len(candidates)} candidate(s) → prioritized, '
                f'sending top {sent_count} to LLM ({skipped} skipped)'
            )
            for rank, c in enumerate(prioritized[:10], 1):
                _pipeline_log(
                    f'[gmail]   rank {rank} score={_subscription_signal_score(c)} '
                    f'| {c["subject"][:50]}'
                )

        extracted = llm.extract_subscriptions(prioritized)
    except Exception as exc:  # noqa: BLE001 - always answer JSON, never HTML
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'analyze failed: {exc}'}, status=500)

    # De-duplicate by platform + plan (same service twice → keep richer entry).
    deduped = {}
    for item in extracted:
        key = f"{item['platform'].lower()}|{(item.get('plan_name') or '').lower()}"
        existing = deduped.get(key)
        if existing is None or (existing.get('payment_amount') is None and item.get('payment_amount')):
            deduped[key] = item

    from subscriptions.platform_utils import resolve_official_platform

    subscriptions_out = []
    skipped_unofficial = 0
    for item in deduped.values():
        platform = resolve_official_platform(name=item.get('platform'))
        if not platform:
            skipped_unofficial += 1
            if _pipeline_logging_enabled():
                _pipeline_log(f'[gmail] skip unofficial: {item.get("platform")}')
            continue
        enriched = dict(item)
        enriched['platform'] = platform.name
        enriched['is_official'] = True
        enriched['platform_id'] = platform.id
        subscriptions_out.append(enriched)

    if _pipeline_logging_enabled():
        _pipeline_log(
            f'[gmail] LLM extracted {len(extracted)} → deduped to {len(deduped)} '
            f'→ official {len(subscriptions_out)} (skipped {skipped_unofficial})'
        )
        for sub in subscriptions_out:
            _pipeline_log(
                f'[gmail]   · {sub.get("platform")} | {sub.get("plan_name") or "-"} '
                f'| {sub.get("payment_amount")} | {sub.get("billing_cycle")} '
                f'| renew={sub.get("renewal_date")}'
            )
        _pipeline_log('[gmail] gmail_analyze done')

    payload = {
        'subscriptions': subscriptions_out,
        'scanned': len(candidates),
        'scan_meta': scan_meta,
        'skipped_unofficial': skipped_unofficial,
    }
    if debug:
        payload['debug'] = {
            'fetched': len(trace),
            'passed_filter': len(candidates),
            'llm_sent': sent_count,
            'llm_skipped': skipped,
            'emails': trace,
            'llm_raw': extracted,
            'prioritized_ranking': [
                {
                    'rank': i + 1,
                    'score': _subscription_signal_score(c),
                    'sent_to_llm': i < sent_count,
                    'subject': c['subject'],
                    'sender': c['sender'],
                }
                for i, c in enumerate(prioritized[:40])
            ],
            'candidates_sent_to_llm': [
                {
                    'rank': i + 1,
                    'score': _subscription_signal_score(c),
                    'subject': c['subject'],
                    'sender': c['sender'],
                    'body_preview': c['body'][:300],
                }
                for i, c in enumerate(prioritized[:sent_count])
            ],
        }

    return JsonResponse(payload, json_dumps_params={'ensure_ascii': False})

