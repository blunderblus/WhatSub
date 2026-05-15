from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    nickname = models.CharField(max_length=30)
    profile_image = models.URLField(blank=True, null=True)