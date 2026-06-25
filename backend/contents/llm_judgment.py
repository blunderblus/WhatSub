"""LLM judgment layer for benchmark scoring (cached, temperature=0, JSON only)."""
import hashlib
import json
import logging
import re

import requests

from detector.ai_client import build_chat_payload, chat_completions_url, chat_headers
from django.conf import settings

from .models import LLMJudgmentCache

logger = logging.getLogger(__name__)

_TIMEOUT = 90
_SYSTEM_PROMPT = (
    'You are a precise analyst for streaming subscription benchmarks in South Korea. '
    'Reply ONLY with strict JSON matching the requested schema. No prose.'
)


def is_configured():
    return bool(getattr(settings, 'AI_API_KEY', '')) and bool(getattr(settings, 'AI_API_BASE', ''))


def _content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def _parse_json(content):
    text = (content or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?', '', text).strip()
        text = re.sub(r'```$', '', text).strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _call_llm(prompt, model=None):
    url = chat_completions_url()
    payload = build_chat_payload(
        messages=[
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ],
        use_json_format=True,
        model=model,
    )
    headers = chat_headers()
    resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
    resp.raise_for_status()
    return _parse_json(resp.json()['choices'][0]['message']['content'])


def get_llm_judgment(
    cache_key,
    prompt,
    snapshot_date,
    judgment_type,
    target_id='batch',
    schema_hint=None,
    model=None,
):
    """
    Idempotent LLM judgment with DB cache.

    ``cache_key`` should be stable for the same inputs (often includes content-hash).
    Returns parsed JSON dict from cache or fresh LLM call.
    """
    cached = LLMJudgmentCache.objects.filter(cache_key=cache_key).first()
    if cached:
        logger.info('[llm_judgment] cache hit: %s', cache_key)
        return cached.result_json

    if not is_configured():
        logger.warning('[llm_judgment] LLM not configured, skipping %s', cache_key)
        return None

    full_prompt = prompt
    if schema_hint:
        full_prompt = f'{prompt}\n\nRequired JSON schema:\n{schema_hint}'

    logger.info('[llm_judgment] calling LLM: %s', cache_key)
    try:
        result = _call_llm(full_prompt, model=model)
    except Exception as exc:
        logger.warning('[llm_judgment] failed %s: %s', cache_key, exc)
        return None

    LLMJudgmentCache.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            'judgment_type': judgment_type,
            'target_id': str(target_id),
            'result_json': result,
            'snapshot_date': snapshot_date,
        },
    )
    return result


def build_cache_key(judgment_type, snapshot_date, platform_id, prompt):
    """Content-hash idempotent cache key."""
    digest = _content_hash(prompt)
    return f'{judgment_type}:{snapshot_date}:{platform_id}:{digest}'
