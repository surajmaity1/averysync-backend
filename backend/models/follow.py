from django.db import models
from django.utils import timezone
import uuid
from backend.models.user import UserModel


class UserFollowModel(models.Model):
    class FollowStatus(models.IntegerChoices):
        PENDING = 1
        ACCEPTED = 2

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    follower = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="following_edges"
    )
    followee = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="follower_edges"
    )
    status = models.SmallIntegerField(
        choices=FollowStatus, default=FollowStatus.PENDING
    )
    requested_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "user_follows"
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "followee"], name="uq_follow_pair"
            ),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("followee")),
                name="ck_follow_no_self",
            ),
        ]
        indexes = [
            models.Index(
                fields=["followee"],
                condition=models.Q(status=2, is_deleted=False),
                name="idx_follow_followers",
            ),
            models.Index(
                fields=["follower"],
                condition=models.Q(status=2, is_deleted=False),
                name="idx_follow_following",
            ),
            models.Index(
                fields=["followee"],
                condition=models.Q(status=1, is_deleted=False),
                name="idx_follow_pending",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
