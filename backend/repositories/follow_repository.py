import logging

from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest

from backend.constants.messages import RepositoryError
from backend.models.follow import UserFollowModel
from backend.models.user import UserModel

logger = logging.getLogger(__name__)

ACCEPTED = UserFollowModel.FollowStatus.ACCEPTED
PENDING = UserFollowModel.FollowStatus.PENDING


class FollowRepository:
    @classmethod
    def _apply_counts(cls, follower_id: str, followee_id: str, delta: int) -> None:
        if delta >= 0:
            UserModel.objects.filter(id=followee_id).update(
                follower_count=F("follower_count") + delta
            )
            UserModel.objects.filter(id=follower_id).update(
                following_count=F("following_count") + delta
            )
        else:
            UserModel.objects.filter(id=followee_id).update(
                follower_count=Greatest(F("follower_count") + delta, Value(0))
            )
            UserModel.objects.filter(id=follower_id).update(
                following_count=Greatest(F("following_count") + delta, Value(0))
            )

    @classmethod
    @transaction.atomic
    def create_or_reactivate(
        cls,
        follower_id: str,
        followee_id: str,
        target_status: int,
        requested_at,
        responded_at=None,
    ) -> tuple[UserFollowModel, bool]:
        try:
            existing = (
                UserFollowModel.objects.select_for_update()
                .filter(follower_id=follower_id, followee_id=followee_id)
                .first()
            )
            prior_active_accepted = bool(
                existing and not existing.is_deleted and existing.status == ACCEPTED
            )

            edge, created = UserFollowModel.objects.update_or_create(
                follower_id=follower_id,
                followee_id=followee_id,
                defaults={
                    "status": target_status,
                    "requested_at": requested_at,
                    "responded_at": responded_at,
                    "is_deleted": False,
                },
                create_defaults={
                    "status": target_status,
                    "requested_at": requested_at,
                    "responded_at": responded_at,
                    "is_deleted": False,
                    "created_by": follower_id,
                },
            )

            new_accepted = target_status == ACCEPTED
            if new_accepted and not prior_active_accepted:
                cls._apply_counts(follower_id, followee_id, 1)
            elif prior_active_accepted and not new_accepted:
                cls._apply_counts(follower_id, followee_id, -1)

            return edge, created
        except Exception as exception:
            logger.error(f"Failed to upsert follow edge: {str(exception)}")
            raise ValueError(
                RepositoryError.FOLLOW_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def get_edge(
        cls, follower_id: str, followee_id: str, for_update: bool = False
    ) -> UserFollowModel | None:
        try:
            queryset = UserFollowModel.objects.filter(
                follower_id=follower_id, followee_id=followee_id
            )
            if for_update:
                queryset = queryset.select_for_update()
            return queryset.first()
        except Exception as exception:
            logger.error(f"Failed to fetch follow edge: {str(exception)}")
            raise ValueError(RepositoryError.FOLLOW_FETCH_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def accept(
        cls, follower_id: str, followee_id: str, responded_at
    ) -> UserFollowModel | None:
        try:
            edge = (
                UserFollowModel.objects.select_for_update()
                .filter(
                    follower_id=follower_id,
                    followee_id=followee_id,
                    is_deleted=False,
                )
                .first()
            )
            if edge is None:
                return None
            if edge.status == ACCEPTED:
                return edge

            edge.status = ACCEPTED
            edge.responded_at = responded_at
            edge.save()
            cls._apply_counts(follower_id, followee_id, 1)
            return edge
        except Exception as exception:
            logger.error(f"Failed to accept follow edge: {str(exception)}")
            raise ValueError(
                RepositoryError.FOLLOW_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def soft_delete(
        cls, follower_id: str, followee_id: str, expected_status: int | None = None
    ) -> UserFollowModel | None:
        try:
            edge = (
                UserFollowModel.objects.select_for_update()
                .filter(
                    follower_id=follower_id,
                    followee_id=followee_id,
                    is_deleted=False,
                )
                .first()
            )
            if edge is None:
                return None
            if expected_status is not None and edge.status != expected_status:
                return None

            was_accepted = edge.status == ACCEPTED
            edge.is_deleted = True
            edge.save()
            if was_accepted:
                cls._apply_counts(follower_id, followee_id, -1)
            return edge
        except Exception as exception:
            logger.error(f"Failed to soft-delete follow edge: {str(exception)}")
            raise ValueError(
                RepositoryError.FOLLOW_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def exists_accepted(cls, follower_id: str, followee_id: str) -> bool:
        try:
            return UserFollowModel.objects.filter(
                follower_id=follower_id,
                followee_id=followee_id,
                status=ACCEPTED,
                is_deleted=False,
            ).exists()
        except Exception as exception:
            logger.error(f"Failed to fetch follow edge: {str(exception)}")
            raise ValueError(RepositoryError.FOLLOW_FETCH_FAILED.format(str(exception)))

    @classmethod
    def list_followers(
        cls, user_id: str, limit: int, offset: int
    ) -> tuple[list[UserFollowModel], int]:
        return cls._list(
            filters={"followee_id": user_id, "status": ACCEPTED},
            related="follower",
            ordering=("-responded_at", "-created_at"),
            limit=limit,
            offset=offset,
        )

    @classmethod
    def list_following(
        cls, user_id: str, limit: int, offset: int
    ) -> tuple[list[UserFollowModel], int]:
        return cls._list(
            filters={"follower_id": user_id, "status": ACCEPTED},
            related="followee",
            ordering=("-responded_at", "-created_at"),
            limit=limit,
            offset=offset,
        )

    @classmethod
    def list_pending(
        cls, user_id: str, limit: int, offset: int
    ) -> tuple[list[UserFollowModel], int]:
        return cls._list(
            filters={"followee_id": user_id, "status": PENDING},
            related="follower",
            ordering=("-requested_at", "-created_at"),
            limit=limit,
            offset=offset,
        )

    @classmethod
    def _list(
        cls, filters: dict, related: str, ordering: tuple, limit: int, offset: int
    ) -> tuple[list[UserFollowModel], int]:
        try:
            base = UserFollowModel.objects.filter(is_deleted=False, **filters)
            total = base.count()
            rows = list(
                base.select_related(related).order_by(*ordering)[
                    offset : offset + limit
                ]
            )
            return rows, total
        except Exception as exception:
            logger.error(f"Failed to list follow edges: {str(exception)}")
            raise ValueError(RepositoryError.FOLLOW_LIST_FAILED.format(str(exception)))
