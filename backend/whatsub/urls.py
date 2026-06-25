"""
URL configuration for whatsub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include, re_path
from django.views.static import serve


def health(_request):
    return HttpResponse('ok', content_type='text/plain')


urlpatterns = [
    path('health/', health, name='health'),
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
    path('accounts/', include('accounts.page_urls')),
    path('accounts/', include('allauth.urls')),
    path('detector/', include(('detector.urls', 'detector'), namespace='detector')),
    path('api/detector/', include(('detector.urls', 'detector_api'), namespace='detector_api')),
    path('api/contents/', include('contents.urls')),
    path('api/community/', include('community.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # django.conf.urls.static.static() is DEBUG-only; serve platform icons in production.
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
