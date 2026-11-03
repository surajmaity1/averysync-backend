import logging

from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest

from backend.constants.messages import RepositoryError
from backend.models.post import PostModel
from backend.models.post_like import PostLikeModel

logger = logging.getLogger(__name__)


class PostLikeRepository:
    @classmethod
    def _lock_active_post(cls, post_id: str) -> PostModel | None:
        return (
            PostModel.objects.select_for_update()
            .filter(id=post_id, is_deleted=False)
            .first()
        )

    @classmethod
    @transaction.atomic
    def like(cls, user_id: str, post_id: str, now) -> int | None:
        try:
            post = cls._lock_active_post(post_id)
            if post is None:
                return None

            existing = (
                PostLikeModel.objects.select_for_update()
                .filter(post_id=post_id, user_id=user_id)
                .first()
            )
            was_active = bool(existing and not existing.is_deleted)

            PostLikeModel.objects.update_or_create(
                post_id=post_id,
                user_id=user_id,
                defaults={"is_deleted": False},
                create_defaults={"is_deleted": False, "created_by": user_id},
            )

            if not was_active:
                PostModel.objects.filter(id=post_id).update(
                    like_count=F("like_count") + 1
                )
                post.refresh_from_db(fields=["like_count"])

            return post.like_count
        except Exception as exception:
            logger.error(f"Failed to like post: {str(exception)}")
            raise ValueError(RepositoryError.LIKE_UPSERT_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def unlike(cls, user_id: str, post_id: str) -> int | None:
        try:
            post = cls._lock_active_post(post_id)
            if post is None:
                return None

            existing = (
                PostLikeModel.objects.select_for_update()
                .filter(post_id=post_id, user_id=user_id, is_deleted=False)
                .first()
            )
            if existing is not None:
                existing.is_deleted = True
                existing.save()
                PostModel.objects.filter(id=post_id).update(
                    like_count=Greatest(F("like_count") - 1, Value(0))
                )
                post.refresh_from_db(fields=["like_count"])

            return post.like_count
        except Exception as exception:
            logger.error(f"Failed to unlike post: {str(exception)}")
            raise ValueError(RepositoryError.LIKE_UPSERT_FAILED.format(str(exception)))

    @classmethod
    def is_liked(cls, user_id: str, post_id: str) -> bool:
        try:
            return PostLikeModel.objects.filter(
                user_id=user_id, post_id=post_id, is_deleted=False
            ).exists()
        except Exception as exception:
            logger.error(f"Failed to fetch post like: {str(exception)}")
            raise ValueError(RepositoryError.LIKE_FETCH_FAILED.format(str(exception)))

    @classmethod
    def liked_post_ids(cls, user_id: str, post_ids: list[str]) -> set[str]:
        if not post_ids:
            return set()
        try:
            rows = PostLikeModel.objects.filter(
                user_id=user_id, post_id__in=post_ids, is_deleted=False
            ).values_list("post_id", flat=True)
            return {str(post_id) for post_id in rows}
        except Exception as exception:
            logger.error(f"Failed to fetch post likes: {str(exception)}")
            raise ValueError(RepositoryError.LIKE_FETCH_FAILED.format(str(exception)))
