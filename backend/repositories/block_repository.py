import logging

from django.db import transaction
from django.db.models import Q

from backend.constants.messages import RepositoryError
from backend.models.block import UserBlockModel

logger = logging.getLogger(__name__)


class BlockRepository:
    @classmethod
    @transaction.atomic
    def create_or_reactivate(
        cls, blocker_id: str, blocked_id: str
    ) -> tuple[UserBlockModel, bool]:
        try:
            block, created = UserBlockModel.objects.update_or_create(
                blocker_id=blocker_id,
                blocked_id=blocked_id,
                defaults={"is_deleted": False},
                create_defaults={"is_deleted": False, "created_by": blocker_id},
            )
            return block, created
        except Exception as exception:
            logger.error(f"Failed to upsert block: {str(exception)}")
            raise ValueError(RepositoryError.BLOCK_UPSERT_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def soft_delete(cls, blocker_id: str, blocked_id: str) -> UserBlockModel | None:
        try:
            block = (
                UserBlockModel.objects.select_for_update()
                .filter(blocker_id=blocker_id, blocked_id=blocked_id, is_deleted=False)
                .first()
            )
            if block is None:
                return None
            block.is_deleted = True
            block.save()
            return block
        except Exception as exception:
            logger.error(f"Failed to soft-delete block: {str(exception)}")
            raise ValueError(RepositoryError.BLOCK_UPSERT_FAILED.format(str(exception)))

    @classmethod
    def is_blocked(cls, one_user: str, another_user: str) -> bool:
        try:
            return (
                UserBlockModel.objects.filter(is_deleted=False)
                .filter(
                    Q(blocker_id=one_user, blocked_id=another_user)
                    | Q(blocker_id=another_user, blocked_id=one_user)
                )
                .exists()
            )
        except Exception as exception:
            logger.error(f"Failed to fetch block: {str(exception)}")
            raise ValueError(RepositoryError.BLOCK_FETCH_FAILED.format(str(exception)))

    @classmethod
    def list_blocks(
        cls, user_id: str, limit: int, offset: int
    ) -> tuple[list[UserBlockModel], int]:
        try:
            base = UserBlockModel.objects.filter(blocker_id=user_id, is_deleted=False)
            total = base.count()
            rows = list(
                base.select_related("blocked").order_by("-created_at")[
                    offset : offset + limit
                ]
            )
            return rows, total
        except Exception as exception:
            logger.error(f"Failed to list blocks: {str(exception)}")
            raise ValueError(RepositoryError.BLOCK_FETCH_FAILED.format(str(exception)))
