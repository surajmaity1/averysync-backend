from backend.constants.messages import RepositoryError
from backend.models.post import PostModel
from django.db import transaction
import logging
from typing import List, Optional

from backend.constants.post import SpaceStatus

logger = logging.getLogger(__name__)


class PostRepository:
    @classmethod
    @transaction.atomic
    def create(cls, post: PostModel) -> PostModel:
        try:
            created_post = PostModel.objects.create(
                title=post.title,
                description=post.description,
                type=post.type,
                is_recorded=post.is_recorded,
                created_at=post.created_at,
                updated_at=post.updated_at,
                created_by=post.created_by,
                updated_by=post.updated_by,
                status=post.status,
            )
            return created_post
        except Exception as exception:
            logger.error(f"Failed to create post: {str(exception)}")
            raise ValueError(
                RepositoryError.POST_CREATION_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def get_posts(cls) -> List[PostModel]:
        try:
            posts = PostModel.objects.filter(is_deleted=False).order_by("-created_at")
            return posts
        except Exception as exception:
            logger.error(f"Failed to fetch all post: {str(exception)}")
            raise ValueError(RepositoryError.POST_FETCH_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def get_by_id(cls, post_id: str) -> PostModel | None:
        try:
            post = PostModel.objects.get(id=post_id, is_deleted=False)
            return post
        except Exception as exception:
            logger.error(f"Failed to fetch post: {str(exception)}")
            raise ValueError(RepositoryError.POST_FETCH_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def update_by_id(cls, post_id: str, update_data: dict) -> Optional[PostModel]:
        try:
            post = PostModel.objects.select_for_update().get(
                id=post_id, is_deleted=False
            )

            status = update_data.get("status") or SpaceStatus["SCHEDULED"].name

            if hasattr(status, "value"):
                status = status.value

            post_update_data = {
                "title": update_data.get("title"),
                "description": update_data.get("description"),
                "is_recorded": update_data.get("isRecorded"),
                "scheduled_started_at": update_data.get("scheduledStartedAt"),
                "scheduled_ended_at": update_data.get("scheduledEndedAt"),
                "started_at": update_data.get("startedAt"),
                "ended_at": update_data.get("endedAt"),
                "created_in_timezone": update_data.get("createdInTimezone"),
                "status": SpaceStatus[status].value,
                "updated_at": update_data.get("updated_at"),
            }

            update_data = {
                key: value
                for key, value in post_update_data.items()
                if value is not None
            }

            for field, value in update_data.items():
                if hasattr(post, field):
                    setattr(post, field, value)

            post.save()

            return post
        except Exception as exception:
            logger.error(f"Failed to fetch post: {str(exception)}")
            return None

    @classmethod
    @transaction.atomic
    def delete_by_id(cls, post_id: str) -> bool:
        try:
            post = PostModel.objects.get(id=post_id, is_deleted=False)
            post.is_deleted = True
            post.save()
            return True
        except Exception as exception:
            logger.error(f"Failed to delete post or space: {str(exception)}")
            raise ValueError(RepositoryError.POST_DELETE_FAILED.format(post_id))
