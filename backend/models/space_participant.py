from django.db import models
from django.utils import timezone
import uuid
from backend.models.post import PostModel
from backend.models.user import UserModel


class SpaceParticipantModel(models.Model):
    class ParticipantRole(models.IntegerChoices):
        HOST = 1
        COHOST = 2
        SPEAKER = 3
        LISTENER = 4

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    post = models.ForeignKey(
        PostModel, on_delete=models.CASCADE, related_name="post_participants"
    )
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="user_participations"
    )
    role = models.SmallIntegerField(
        choices=ParticipantRole, default=ParticipantRole.LISTENER
    )
    first_joined_at = models.DateTimeField()
    last_joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    muted_by = models.CharField(max_length=100, null=True, blank=True)
    muted_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "space_participants"
        constraints = [
            models.UniqueConstraint(
                fields=["post", "user"], name="uq_participant_post_user"
            )
        ]
        indexes = [
            models.Index(
                fields=["post"],
                condition=models.Q(left_at__isnull=True),
                name="idx_participant_active",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
