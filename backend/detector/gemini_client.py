"""GMS Gemini generateContent API helpers (receipt vision, etc.)."""

import json
import logging

import requests
from django.conf import settings

from .gms_auth import append_gms_key, gms_api_key, gms_json_headers

logger = logging.getLogger(__name__)

DEFAULT_VISION_MODEL = 'gemini-2.5-flash'
DEFAULT_VISION_API_BASE = (
    'https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com/v1beta'
)


def resolve_vision_model() -> str:
    raw = getattr(settings, 'AI_VISION_MODEL', '') or getattr(settings, 'AI_MODEL', '') or ''
    model = str(raw).strip().strip("'\"")
    return model or DEFAULT_VISION_MODEL


def vision_api_base() -> str:
    base = getattr(settings, 'AI_VISION_API_BASE', '') or DEFAULT_VISION_API_BASE
    return str(base).rstrip('/')


def is_vision_configured() -> bool:
    return bool(gms_api_key()) and bool(vision_api_base())


def generate_content_url(model: str | None = None) -> str:
    model = model or resolve_vision_model()
    url = f'{vision_api_base()}/models/{model}:generateContent'
    return append_gms_key(url)


def build_generate_content_payload(
    *,
    system_prompt: str,
    user_parts: list,
    json_response: bool = True,
) -> dict:
    payload = {
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'contents': [{'role': 'user', 'parts': user_parts}],
        'generationConfig': {'temperature': 0},
    }
    if json_response:
        payload['generationConfig']['responseMimeType'] = 'application/json'
    return payload


def estimate_payload_bytes(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False))


def extract_text(body: dict) -> str:
    candidates = body.get('candidates') or []
    if not candidates:
        raise ValueError('Gemini response had no candidates')
    parts = (candidates[0].get('content') or {}).get('parts') or []
    text = ''.join(part.get('text', '') for part in parts if part.get('text'))
    if not text.strip():
        raise ValueError('Gemini response had no text content')
    return text


def post_generate_content(
    *,
    system_prompt: str,
    user_parts: list,
    json_response: bool = True,
    timeout: int = 120,
) -> str:
    model = resolve_vision_model()
    payload = build_generate_content_payload(
        system_prompt=system_prompt,
        user_parts=user_parts,
        json_response=json_response,
    )
    url = generate_content_url(model)
    logger.info(
        '[gemini_client] generateContent model=%s payload=%dB',
        model,
        estimate_payload_bytes(payload),
    )
    resp = requests.post(url, json=payload, headers=gms_json_headers(), timeout=timeout)
    resp.raise_for_status()
    return extract_text(resp.json())
