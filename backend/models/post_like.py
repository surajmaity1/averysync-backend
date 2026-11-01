from django.db import models
from django.utils import timezone
import uuid

from backend.models.post import PostModel
from backend.models.user import UserModel


class PostLikeModel(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    post = models.ForeignKey(PostModel, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE, related_name="post_likes"
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=100)

    class Meta:
        db_table = "post_likes"
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="uq_post_like_pair"),
        ]
        indexes = [
            models.Index(
                fields=["post"],
                condition=models.Q(is_deleted=False),
                name="idx_post_like_active",
            ),
            models.Index(
                fields=["user"],
                condition=models.Q(is_deleted=False),
                name="idx_post_like_by_user",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
