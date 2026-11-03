from django.db import models
from django.utils import timezone
import uuid

from backend.models.conversation import ConversationModel
from backend.models.user import UserModel


class MessageModel(models.Model):
    class MessageType(models.IntegerChoices):
        TEXT = 1
        # Reserved for a future media/attachments doc; TEXT is the only active
        # type in v1.
        IMAGE = 2
        VIDEO = 3
        VOICE = 4
        LINK = 5
        SYSTEM = 6

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    conversation = models.ForeignKey(
        ConversationModel, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="sent_messages"
    )
    type = models.SmallIntegerField(choices=MessageType, default=MessageType.TEXT)
    body = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    client_message_id = models.CharField(max_length=64, null=True, blank=True)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_deleted = models.BooleanField(default=False)
    deleted_for_everyone_at = models.DateTimeField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sender", "client_message_id"],
                condition=models.Q(client_message_id__isnull=False),
                name="uq_message_client_id",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"], name="idx_message_history"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
