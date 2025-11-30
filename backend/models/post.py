from django.db import models
from django.utils import timezone
import uuid
from backend.constants.post import PostType


class PostModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=300, null=True, blank=True)
    type = models.CharField(max_length=10, default=PostType.POST.name)
    is_recorded = models.BooleanField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'posts'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['type']),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
