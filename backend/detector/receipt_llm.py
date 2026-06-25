"""LLM vision extraction for subscription receipts and payment screenshots."""
import base64
import logging

import requests

from .gemini_client import (
    build_generate_content_payload,
    estimate_payload_bytes,
    is_vision_configured,
    post_generate_content,
    resolve_vision_model,
)
from .llm import _parse_content

logger = logging.getLogger('detector.receipt')

_TIMEOUT = 120
_MAX_IMAGES = 5
_GMS_PAYLOAD_LIMIT = 95_000

_SYSTEM_PROMPT = (
    'You are a precise assistant that extracts recurring subscription billing '
    'information from payment receipts, billing screenshots, and app store '
    'subscription pages. Reply ONLY with strict JSON, no prose.'
)

_USER_PROMPT = (
    'Analyze the attached receipt or subscription payment screenshot(s). '
    'Identify every RECURRING subscription / membership / streaming service shown.\n\n'
    'Ignore one-time purchases, shipping receipts, and pure promotions.\n\n'
    'Return a JSON object with a single key "subscriptions" whose value is an array. '
    'Each item must have exactly these keys:\n'
    '  "platform": canonical service name (e.g. "Netflix", "Disney+", "TVING", '
    '"Wavve", "Watcha", "YouTube Premium", "Spotify", "ChatGPT Plus").\n'
    '  "plan_name": plan/tier name if visible, else "".\n'
    '  "payment_amount": integer KRW amount (digits only). Use null if unclear.\n'
    '  "billing_cycle": one of "monthly", "annual", "weekly", else "monthly".\n'
    '  "renewal_date": "YYYY-MM-DD" if a next billing date is visible, else null.\n'
    '  "payment_method": card/wallet label if visible (e.g. "신한카드", "Apple Pay"), else "".\n\n'
    'If none are subscriptions, return {"subscriptions": []}.\n\n'
    'Respond in json format only.'
)


def _extract_api_error_message(response) -> str:
    if response is None:
        return ''
    try:
        body = response.json()
    except (ValueError, TypeError):
        return (response.text or '')[:280]

    nested = body.get('error')
    if isinstance(nested, dict):
        inner = nested.get('error')
        if isinstance(inner, dict) and inner.get('message'):
            return str(inner['message'])[:280]
        if nested.get('message'):
            return str(nested['message'])[:280]

    if body.get('message'):
        return str(body['message'])[:280]
    return (response.text or '')[:280]


def _format_gms_error(detail: str, *, payload_bytes: int) -> str:
    if 'contents is not specified' in detail:
        return (
            f'영수증 이미지 전송 크기({payload_bytes // 1024}KB)가 GMS 한도를 초과했습니다. '
            '이미지 장수를 줄이거나 더 작은 스크린샷을 업로드해 주세요.'
        )
    if 'Model not found in request' in detail:
        return (
            f'영수증 이미지 전송 크기({payload_bytes // 1024}KB)가 GMS 한도를 초과했습니다. '
            '이미지 장수를 줄이거나 스크린샷을 다시 업로드해 주세요.'
        )
    return detail


def _build_user_parts(images):
    parts = [{'text': _USER_PROMPT}]
    for raw, mime in images:
        mime = mime or 'image/jpeg'
        parts.append({
            'inlineData': {
                'mimeType': mime,
                'data': base64.b64encode(raw).decode('ascii'),
            },
        })
    return parts


def _call_vision_api(images, *, payload_bytes: int) -> str:
    user_parts = _build_user_parts(images)
    try:
        return post_generate_content(
            system_prompt=_SYSTEM_PROMPT,
            user_parts=user_parts,
            json_response=True,
            timeout=_TIMEOUT,
        )
    except requests.HTTPError as exc:
        detail = _extract_api_error_message(exc.response)
        status = exc.response.status_code if exc.response is not None else '?'
        logger.warning(
            '[receipt_llm] gemini HTTP %s model=%s payload=%dB: %s',
            status,
            resolve_vision_model(),
            payload_bytes,
            detail or exc,
        )
        if status == 401:
            raise RuntimeError(
                'GMS API 키가 올바르지 않습니다. .env의 AI_API_KEY(또는 GMS_KEY)를 확인해 주세요.'
            ) from exc
        if status == 429:
            raise RuntimeError('AI API 사용량 한도에 도달했습니다. 잠시 후 다시 시도해 주세요.') from exc
        message = _format_gms_error(
            detail or f'영수증 이미지 분석 API 요청이 거부되었습니다. (HTTP {status})',
            payload_bytes=payload_bytes,
        )
        raise RuntimeError(message) from exc


def _extract_batch(images):
    user_parts = _build_user_parts(images)
    payload = build_generate_content_payload(
        system_prompt=_SYSTEM_PROMPT,
        user_parts=user_parts,
        json_response=True,
    )
    payload_bytes = estimate_payload_bytes(payload)
    if payload_bytes > _GMS_PAYLOAD_LIMIT:
        raise RuntimeError(
            f'영수증 이미지 전송 크기({payload_bytes // 1024}KB)가 GMS 한도를 초과합니다. '
            '이미지 장수를 줄이거나 더 작은 스크린샷을 업로드해 주세요.'
        )
    return _call_vision_api(images, payload_bytes=payload_bytes)


def extract_subscriptions_from_images(images):
    """
    images: list of (bytes, mime_type) tuples.
    Returns normalized subscription dicts (same schema as Gmail LLM).
    """
    if not is_vision_configured() or not images:
        return []

    capped = images[:_MAX_IMAGES]
    logger.info(
        '[receipt_llm] vision request: %d image(s), model=%s',
        len(capped),
        resolve_vision_model(),
    )

    parsed = []
    try:
        if len(capped) == 1:
            parsed = _parse_content(_extract_batch(capped))
        else:
            for raw, mime in capped:
                batch = _extract_batch([(raw, mime)])
                parsed.extend(_parse_content(batch))
    except RuntimeError:
        raise
    except (requests.RequestException, KeyError, ValueError, IndexError) as exc:
        logger.warning('[receipt_llm] vision failed: %s', exc)
        raise RuntimeError('영수증 이미지 분석에 실패했습니다. 잠시 후 다시 시도해 주세요.') from exc

    logger.info('[receipt_llm] parsed %d subscription(s)', len(parsed))
    return parsed
