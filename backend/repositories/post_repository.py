from backend.constants.messages import RepositoryError
from backend.models.post import PostModel
from django.db import transaction
import logging
from typing import List

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
                updated_by=post.updated_by
            )
            logger.info(f'Post created with id: {created_post.id}')
            return created_post
        except Exception as exception:
            logger.error(f'Failed to create post: {str(exception)}')
            raise ValueError(RepositoryError.POST_CREATION_FAILED.format(str(exception)))


    @classmethod
    @transaction.atomic
    def get_posts(cls) -> List[PostModel]:
        try:
            posts = PostModel.objects.filter(is_deleted=False).order_by('-created_at')
            return posts
        except Exception as exception:
            logger.error(f'Failed to fetch all post: {str(exception)}')
            raise ValueError(RepositoryError.POST_FETCH_FAILED.format(str(exception)))


    @classmethod
    @transaction.atomic
    def get_by_id(cls, post_id: str) -> PostModel | None:
        try:
            post = PostModel.objects.get(id=post_id)
            return post
        except Exception as exception:
            logger.error(f'Failed to fetch post: {str(exception)}')
            raise ValueError(RepositoryError.POST_FETCH_FAILED.format(str(exception)))
