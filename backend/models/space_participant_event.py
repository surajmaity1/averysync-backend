from django.db import models
from django.utils import timezone
import uuid
from backend.models.post import PostModel
from backend.models.user import UserModel


class SpaceParticipantEventModel(models.Model):
    class ParticipantAction(models.IntegerChoices):
        JOIN = 1
        LEAVE = 2
        MUTE = 3
        UNMUTE = 4
        REMOVE = 5

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    post = models.ForeignKey(
        PostModel, on_delete=models.CASCADE, related_name="post_participant_events"
    )
    target_user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="user_participant_events"
    )
    actor = models.CharField(max_length=100)
    action = models.SmallIntegerField(choices=ParticipantAction)
    reason = models.CharField(max_length=300, null=True, blank=True)
    muted_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "space_participant_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"], name="idx_pevent_post_time")
        ]
