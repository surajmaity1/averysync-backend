from django.db import models
from django.utils import timezone
import uuid
from backend.models.post import PostModel
from backend.models.user import UserModel


class ReminderModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    post = models.ForeignKey(
        PostModel, on_delete=models.CASCADE, related_name="post_reminders"
    )
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="user_reminders"
    )
    is_reminder_set = models.BooleanField(default=False, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "reminders"
        unique_together = ("post", "user")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["id"]),
            models.Index(fields=["post_id"]),
            models.Index(fields=["created_by"]),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
