"""
LLM-based subscription extraction from Gmail metadata.

Uses an OpenAI-compatible chat-completions endpoint (SSAFY GMS proxy by
default). Candidates are processed in batches; each batch is one API call.
Designed to fail soft: any batch error is skipped so the scan still completes.
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger('detector.gmail')


def _pipeline_log(msg):
    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        logger.info(msg)

_TIMEOUT = 90
_MAX_EMAILS_PER_BATCH = 5
_MAX_LLM_BATCHES = 16  # up to 80 emails per scan
_MAX_BODY_CHARS = 3500
_PER_EMAIL_LLM_THRESHOLD = 35  # above this, fall back to batching

_SYSTEM_PROMPT = (
    'You are a precise assistant that extracts recurring subscription billing '
    'information from email content. You read the full body carefully, not just '
    'the subject. Reply ONLY with strict JSON, no prose.'
)

_USER_TEMPLATE = (
    'Below is a list of emails (subject, sender, and full body text). Identify '
    'every RECURRING subscription / membership / streaming payment and extract '
    'its details. Read the BODY carefully — key facts are often only there:\n'
    '- The subject may say it is a monthly subscription while the price and '
    'plan name appear only inside the body.\n'
    '- A single invoice (e.g. from Apple, Google, or a payment processor) may '
    'list SEVERAL line items; return a separate entry for EACH recurring '
    'subscription item, and ignore one-time purchases.\n'
    '- Third-party transaction/receipt emails may only reveal the actual '
    'service name inside the body text.\n\n'
    'Ignore pure promotions, newsletters, shipping notices, and one-off '
    'purchases.\n\n'
    'Return a JSON object with a single key "subscriptions" whose value is an '
    'array. Each item must have exactly these keys:\n'
    '  "platform": canonical service name in English (e.g. "Netflix", '
    '"Disney+", "TVING", "Wavve", "Watcha", "Coupang Play", "YouTube Premium", '
    '"Spotify", "ChatGPT Plus", "Apple TV+", "iCloud+"). If unknown, best guess '
    'from the body.\n'
    '  "plan_name": plan/tier/item name if present, else "".\n'
    '  "payment_amount": integer KRW amount (digits only). Convert other '
    'currencies is NOT required — if the amount is in another currency, still '
    'return the numeric value you see. Use null if no amount is found.\n'
    '  "billing_cycle": one of "monthly", "annual", "weekly", else "monthly".\n'
    '  "renewal_date": "YYYY-MM-DD" if a next-billing/renewal date is present, '
    'else null.\n\n'
    'If none are subscriptions, return {"subscriptions": []}.\n\n'
    'CRITICAL: Process EVERY email below. Each email may contain a different '
    'subscription — return a separate entry for EACH recurring subscription found '
    'across ALL emails. Do not stop after finding one.\n\n'
    'EMAILS:\n__EMAILS__'
)

_SINGLE_EMAIL_TEMPLATE = (
    'Below is ONE billing/receipt email (subject, sender, full body). Extract '
    'every RECURRING subscription or membership in it. Ignore one-time purchases.\n\n'
    'Return JSON: {"subscriptions": [ ... ]} with keys platform, plan_name, '
    'payment_amount (integer KRW or null), billing_cycle, renewal_date '
    '(YYYY-MM-DD or null).\n\n'
    'EMAIL:\n__EMAIL__'
)

_ALLOWED_CYCLES = {'monthly', 'annual', 'weekly'}


def is_configured():
    return bool(getattr(settings, 'AI_API_KEY', '')) and bool(getattr(settings, 'AI_API_BASE', ''))


def _coerce_amount(value):
    if value in (None, '', False):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.sub(r'[^0-9]', '', str(value))
    return int(digits) if digits else None


def _normalize(items):
    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        platform = (item.get('platform') or '').strip()
        if not platform:
            continue
        cycle = (item.get('billing_cycle') or 'monthly').strip().lower()
        if cycle not in _ALLOWED_CYCLES:
            cycle = 'monthly'
        renewal = item.get('renewal_date')
        if renewal and not re.match(r'^\d{4}-\d{2}-\d{2}$', str(renewal)):
            renewal = None
        cleaned.append({
            'platform': platform,
            'plan_name': (item.get('plan_name') or '').strip(),
            'payment_amount': _coerce_amount(item.get('payment_amount')),
            'billing_cycle': cycle,
            'renewal_date': renewal,
        })
    return cleaned


def _parse_content(content):
    """Extract the JSON object from a model response (handles code fences)."""
    text = (content or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text).strip()
        text = re.sub(r'```$', '', text).strip()
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except (ValueError, TypeError):
            return []
    if isinstance(data, list):
        return _normalize(data)
    if isinstance(data, dict):
        return _normalize(data.get('subscriptions', []))
    return []


def _format_email_block(email, idx=1):
    subject = (email.get('subject') or '').replace('\n', ' ')[:200]
    sender = (email.get('sender') or '').replace('\n', ' ')[:120]
    body = (email.get('body') or email.get('snippet') or '').replace('\r', ' ')
    body = re.sub(r'\s+', ' ', body).strip()[:_MAX_BODY_CHARS]
    return (
        f'--- EMAIL {idx} ---\nSUBJECT: {subject}\nFROM: {sender}\nBODY: {body}',
        subject,
    )


def _extract_batch(emails):
    """Run LLM extraction on a single batch of emails. Returns [] on failure."""
    if not emails:
        return []

    if len(emails) == 1:
        block, subject = _format_email_block(emails[0], 1)
        prompt = _SINGLE_EMAIL_TEMPLATE.replace('__EMAIL__', block)
        log_label = f'1 email ({subject[:48]})'
    else:
        lines = []
        for idx, email in enumerate(emails, 1):
            block, _ = _format_email_block(email, idx)
            lines.append(block)
        prompt = _USER_TEMPLATE.replace('__EMAILS__', '\n\n'.join(lines))
        log_label = f'{len(emails)} email(s)'

    url = settings.AI_API_BASE.rstrip('/') + '/chat/completions'
    payload = {
        'model': getattr(settings, 'AI_MODEL', 'gpt-4o-mini'),
        'messages': [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0,
        'response_format': {'type': 'json_object'},
    }
    headers = {
        'Authorization': f'Bearer {settings.AI_API_KEY}',
        'Content-Type': 'application/json',
    }

    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        _pipeline_log(
            f'[llm] batch: {log_label} → {settings.AI_MODEL} (~{len(prompt)} chars)'
        )

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        content = body['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
        _pipeline_log(f'[llm] batch failed: {exc}')
        return []

    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        _pipeline_log(f'[llm] batch raw: {content[:600]}')

    parsed = _parse_content(content)
    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        _pipeline_log(f'[llm] batch parsed {len(parsed)} subscription(s)')
    return parsed


def extract_subscriptions(emails, on_progress=None):
    """
    Given a list of {subject, sender, body} dicts (already priority-sorted),
    return normalized subscription dicts. Processes in batches when there are
    more emails than ``_MAX_EMAILS_PER_BATCH``.
    """
    if not is_configured() or not emails:
        return []

    cap = _MAX_EMAILS_PER_BATCH * _MAX_LLM_BATCHES
    to_process = emails[:cap]
    if len(emails) > cap and getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        _pipeline_log(f'[llm] capping at {cap} emails ({len(emails) - cap} skipped)')

    all_parsed = []
    if len(to_process) <= _PER_EMAIL_LLM_THRESHOLD:
        for idx, email in enumerate(to_process, 1):
            if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
                subj = (email.get('subject') or '')[:56]
                _pipeline_log(f'[llm] per-email {idx}/{len(to_process)}: {subj}')
            if on_progress:
                on_progress(idx, len(to_process), email.get('subject') or '')
            batch_result = _extract_batch([email])
            for sub in batch_result:
                sub['source_subject'] = email.get('source_subject') or email.get('subject') or ''
            all_parsed.extend(batch_result)
    else:
        for start in range(0, len(to_process), _MAX_EMAILS_PER_BATCH):
            batch = to_process[start:start + _MAX_EMAILS_PER_BATCH]
            batch_num = start // _MAX_EMAILS_PER_BATCH + 1
            if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
                _pipeline_log(f'[llm] batch {batch_num} emails {start + 1}–{start + len(batch)}')
            if on_progress:
                on_progress(start + len(batch), len(to_process), batch[0].get('subject') or '')
            all_parsed.extend(_extract_batch(batch))

    if getattr(settings, 'GMAIL_PIPELINE_LOG', True):
        _pipeline_log(f'[llm] total parsed {len(all_parsed)} subscription(s) from all batches')
    return all_parsed
