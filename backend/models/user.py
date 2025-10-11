from django.db import models
from django.utils import timezone


class UserModel(models.Model):
    user_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500, null=True, blank=True)
    sign_in_provider = models.CharField(max_length=20, null=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)