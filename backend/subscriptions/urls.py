from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('catalog/',              views.catalog,           name='catalog'),
    path('platforms/',           views.platform_list,    name='platform_list'),
    path('platforms/<int:pk>/',  views.platform_detail,  name='platform_detail'),
    path('plans/',               views.plan_list,         name='plan_list'),
    path('bundles/',             views.bundle_list,       name='bundle_list'),
    path('passes/',              views.addon_pass_list,   name='addon_pass_list'),
]
