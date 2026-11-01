from django.db import models
from django.utils import timezone
import uuid


class ConversationModel(models.Model):
    class ConversationType(models.IntegerChoices):
        DIRECT = 1
        GROUP = 2

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    type = models.SmallIntegerField(choices=ConversationType)
    # Deterministic "<minUuid>:<maxUuid>" for DIRECT; NULL for GROUP. The partial
    # unique constraint collapses (A,B) and (B,A) onto one live DM.
    dm_key = models.CharField(max_length=80, null=True, blank=True)
    title = models.CharField(max_length=150, null=True, blank=True)
    image = models.URLField(max_length=500, null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=300, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "conversations"
        constraints = [
            models.UniqueConstraint(
                fields=["dm_key"],
                condition=models.Q(type=1, is_deleted=False),
                name="uq_direct_dm_key",
            ),
        ]
        indexes = [
            models.Index(fields=["last_message_at"], name="idx_conv_last_message"),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
