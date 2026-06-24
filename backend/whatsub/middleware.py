from urllib.parse import urlparse

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

_LOCAL_DEV_HOSTS = frozenset({'127.0.0.1', 'localhost', '[::1]'})


class DevRelaxedCsrfMiddleware(CsrfViewMiddleware):
    """DEBUG에서는 Vite 포트가 바뀌어도 loopback Origin을 허용."""

    def _origin_verified(self, request):
        if settings.DEBUG:
            origin = request.META.get('HTTP_ORIGIN')
            if origin:
                hostname = urlparse(origin).hostname
                if hostname in _LOCAL_DEV_HOSTS:
                    return True
        return super()._origin_verified(request)
