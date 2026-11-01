from django.db import models
from django.utils import timezone
import uuid

from backend.models.conversation import ConversationModel
from backend.models.user import UserModel


class ConversationMemberModel(models.Model):
    class MemberRole(models.IntegerChoices):
        OWNER = 1
        ADMIN = 2
        MEMBER = 3

    class MemberState(models.IntegerChoices):
        # PENDING = a message request awaiting the member's accept/decline.
        PENDING = 1
        ACCEPTED = 2

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    conversation = models.ForeignKey(
        ConversationModel, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="conversation_memberships"
    )
    role = models.SmallIntegerField(choices=MemberRole, default=MemberRole.MEMBER)
    state = models.SmallIntegerField(choices=MemberState, default=MemberState.ACCEPTED)
    invited_by = models.CharField(max_length=100, null=True, blank=True)
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    # Read-receipt / mute columns are provisioned here so the full chat feature
    # (read receipts, timed mute) extends without another migration; this slice
    # does not maintain them.
    last_read_message_id = models.UUIDField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.IntegerField(default=0)
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "conversation_members"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"], name="uq_member_conv_user"
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "state"],
                condition=models.Q(left_at__isnull=True, is_deleted=False),
                name="idx_member_inbox",
            ),
            models.Index(
                fields=["conversation"],
                condition=models.Q(left_at__isnull=True, is_deleted=False),
                name="idx_member_active",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
