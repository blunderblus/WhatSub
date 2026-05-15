from django.contrib import admin
from .models import Category, Platform, UserSubscription
# Register your models here.
admin.site.register(Category)
admin.site.register(Platform)
admin.site.register(UserSubscription)
