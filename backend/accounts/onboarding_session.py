"""Session state for resumable onboarding chat flows."""

ONBOARDING_METHOD_KEYS = ('gmail', 'receipt', 'manual')

SESSION_KEY = 'onboarding_chat_resume'


def get_chat_resume(request):
    raw = request.session.get(SESSION_KEY) or {}
    if not isinstance(raw, dict):
        return {}
    step = raw.get('step')
    if not step:
        return {}
    return {
        'step': step,
        'method_key': raw.get('method_key') or '',
        'method_index': raw.get('method_index', 0),
        'skipped_sub': bool(raw.get('skipped_sub')),
    }


def set_chat_resume(request, step, **extra):
    payload = {'step': step, **extra}
    request.session[SESSION_KEY] = payload
    request.session.modified = True


def clear_chat_resume(request):
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]
        request.session.modified = True


def touch_method_pick(request, method_key, method_index=0):
    if method_key not in ONBOARDING_METHOD_KEYS:
        return
    set_chat_resume(
        request,
        step='method_pick',
        method_key=method_key,
        method_index=int(method_index),
    )
