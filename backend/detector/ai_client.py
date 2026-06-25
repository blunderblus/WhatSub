"""Shared GMS / OpenAI-compatible chat-completions helpers."""

from django.conf import settings

DEFAULT_AI_MODEL = 'gpt-4o-mini'
DEFAULT_SCORING_MODEL = 'gpt-5.2'
DEFAULT_INSIGHT_MODEL = 'gpt-5.5'


def _resolve_model_setting(name: str, default: str) -> str:
    raw = getattr(settings, name, '') or ''
    model = str(raw).strip().strip("'\"")
    return model or default


def resolve_ai_model() -> str:
    """Return a non-empty model id (GMS rejects requests without model)."""
    return _resolve_model_setting('AI_MODEL', DEFAULT_AI_MODEL)


def resolve_scoring_model() -> str:
    """Benchmark batch scoring LLM (exclusivity weight, price beneficial)."""
    return _resolve_model_setting('AI_SCORING_MODEL', DEFAULT_SCORING_MODEL)


def resolve_insight_model() -> str:
    """Platform value insight / consumer-facing benchmark report."""
    return _resolve_model_setting('AI_INSIGHT_MODEL', DEFAULT_INSIGHT_MODEL)


def chat_completions_url() -> str:
    return settings.AI_API_BASE.rstrip('/') + '/chat/completions'


def chat_headers() -> dict:
    return {
        'Authorization': f'Bearer {settings.AI_API_KEY}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def build_chat_payload(*, messages, use_json_format: bool = False, model: str | None = None) -> dict:
    resolved = (model or '').strip() or resolve_ai_model()
    payload = {
        'model': resolved,
        'messages': messages,
        'temperature': 0,
    }
    if use_json_format:
        payload['response_format'] = {'type': 'json_object'}
    return payload


def post_chat_completion(
    *, messages, use_json_format: bool = False, model: str | None = None, timeout: int = 90,
):
    """POST /chat/completions; raises requests.HTTPError on failure."""
    import requests

    payload = build_chat_payload(messages=messages, use_json_format=use_json_format, model=model)
    return requests.post(
        chat_completions_url(),
        json=payload,
        headers=chat_headers(),
        timeout=timeout,
    )
