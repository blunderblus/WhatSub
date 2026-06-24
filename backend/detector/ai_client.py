"""Shared GMS / OpenAI-compatible chat-completions helpers."""

from django.conf import settings

DEFAULT_AI_MODEL = 'gpt-4o-mini'


def resolve_ai_model() -> str:
    """Return a non-empty model id (GMS rejects requests without model)."""
    raw = getattr(settings, 'AI_MODEL', '') or ''
    model = str(raw).strip().strip("'\"")
    return model or DEFAULT_AI_MODEL


def chat_completions_url() -> str:
    return settings.AI_API_BASE.rstrip('/') + '/chat/completions'


def chat_headers() -> dict:
    return {
        'Authorization': f'Bearer {settings.AI_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def build_chat_payload(*, messages, use_json_format: bool = False) -> dict:
    model = resolve_ai_model()
    if not model:
        model = DEFAULT_AI_MODEL
    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0,
    }
    if use_json_format:
        payload['response_format'] = {'type': 'json_object'}
    return payload


def post_chat_completion(*, messages, use_json_format: bool = False, timeout: int = 90):
    """POST /chat/completions; raises requests.HTTPError on failure."""
    import requests

    payload = build_chat_payload(messages=messages, use_json_format=use_json_format)
    return requests.post(
        chat_completions_url(),
        json=payload,
        headers=chat_headers(),
        timeout=timeout,
    )
