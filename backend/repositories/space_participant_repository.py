import logging
from datetime import datetime

from django.db import transaction

from backend.constants.messages import RepositoryError
from backend.models.space_participant import SpaceParticipantModel

logger = logging.getLogger(__name__)


class SpaceParticipantRepository:
    @classmethod
    @transaction.atomic
    def upsert_join(
        cls, post_id: str, user_id: str, role: int, joined_at: datetime
    ) -> tuple[SpaceParticipantModel, bool]:
        try:
            participant, created = (
                SpaceParticipantModel.objects.select_for_update().update_or_create(
                    post_id=post_id,
                    user_id=user_id,
                    defaults={
                        "left_at": None,
                        "last_joined_at": joined_at,
                    },
                    create_defaults={
                        "role": role,
                        "first_joined_at": joined_at,
                        "last_joined_at": joined_at,
                        "created_by": user_id,
                    },
                )
            )
            logger.info(
                f"Participant {'created' if created else 'reactivated'} "
                f"with id: {participant.id}"
            )
            return participant, created
        except Exception as exception:
            logger.error(f"Failed to upsert participant: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def get_active(cls, post_id: str, user_id: str) -> SpaceParticipantModel | None:
        try:
            return SpaceParticipantModel.objects.get(
                post_id=post_id,
                user_id=user_id,
                left_at__isnull=True,
                is_deleted=False,
            )
        except SpaceParticipantModel.DoesNotExist:
            return None
        except Exception as exception:
            logger.error(f"Failed to fetch participant: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    def list_by_post(
        cls, post_id: str, include_left: bool = False
    ) -> list[SpaceParticipantModel]:
        try:
            participants = SpaceParticipantModel.objects.filter(
                post_id=post_id, is_deleted=False
            )
            if not include_left:
                participants = participants.filter(left_at__isnull=True)
            return list(participants.order_by("first_joined_at"))
        except Exception as exception:
            logger.error(f"Failed to fetch participants: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def set_mute(
        cls,
        post_id: str,
        user_id: str,
        muted_until: datetime | None,
        muted_by: str,
        muted_at: datetime,
    ) -> SpaceParticipantModel | None:
        return cls._update_active(
            post_id,
            user_id,
            is_muted=True,
            muted_until=muted_until,
            muted_by=muted_by,
            muted_at=muted_at,
        )

    @classmethod
    @transaction.atomic
    def clear_mute(cls, post_id: str, user_id: str) -> SpaceParticipantModel | None:
        return cls._update_active(
            post_id,
            user_id,
            is_muted=False,
            muted_until=None,
            muted_by=None,
            muted_at=None,
        )

    @classmethod
    @transaction.atomic
    def mark_left(
        cls, post_id: str, user_id: str, left_at: datetime
    ) -> SpaceParticipantModel | None:
        return cls._update_active(post_id, user_id, left_at=left_at)

    @classmethod
    @transaction.atomic
    def close_out(cls, post_id: str, ended_at: datetime) -> int:
        try:
            return SpaceParticipantModel.objects.filter(
                post_id=post_id, left_at__isnull=True, is_deleted=False
            ).update(left_at=ended_at, updated_at=ended_at)
        except Exception as exception:
            logger.error(f"Failed to close out participants: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def _update_active(
        cls, post_id: str, user_id: str, **fields
    ) -> SpaceParticipantModel | None:
        try:
            participant = SpaceParticipantModel.objects.select_for_update().get(
                post_id=post_id,
                user_id=user_id,
                left_at__isnull=True,
                is_deleted=False,
            )
        except SpaceParticipantModel.DoesNotExist:
            return None
        except Exception as exception:
            logger.error(f"Failed to fetch participant: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_FETCH_FAILED.format(str(exception))
            )

        try:
            for field, value in fields.items():
                setattr(participant, field, value)
            participant.save()
            return participant
        except Exception as exception:
            logger.error(f"Failed to update participant: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_UPSERT_FAILED.format(str(exception))
            )
