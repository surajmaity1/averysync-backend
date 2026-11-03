from django.db import models
from django.utils import timezone
import uuid
from backend.models.user import UserModel


class UserBlockModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    blocker = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="blocks_received"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "user_blocks"
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"], name="uq_block_pair"
            ),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F("blocked")),
                name="ck_block_no_self",
            ),
        ]
        indexes = [
            models.Index(
                fields=["blocker"],
                condition=models.Q(is_deleted=False),
                name="idx_block_by_blocker",
            ),
            models.Index(
                fields=["blocked"],
                condition=models.Q(is_deleted=False),
                name="idx_block_by_blocked",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
