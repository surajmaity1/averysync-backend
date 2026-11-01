import logging
from datetime import datetime

from django.db import transaction

from backend.constants.messages import RepositoryError
from backend.models.space_participant_event import SpaceParticipantEventModel

logger = logging.getLogger(__name__)


class SpaceParticipantEventRepository:
    @classmethod
    @transaction.atomic
    def create(
        cls,
        post_id: str,
        target_user_id: str,
        actor: str,
        action: int,
        reason: str | None = None,
        muted_until: datetime | None = None,
    ) -> SpaceParticipantEventModel:
        try:
            return SpaceParticipantEventModel.objects.create(
                post_id=post_id,
                target_user_id=target_user_id,
                actor=actor,
                action=action,
                reason=reason,
                muted_until=muted_until,
            )
        except Exception as exception:
            logger.error(f"Failed to create participant event: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_EVENT_CREATE_FAILED.format(str(exception))
            )

    @classmethod
    def list_by_post(cls, post_id: str) -> list[SpaceParticipantEventModel]:
        try:
            return list(SpaceParticipantEventModel.objects.filter(post_id=post_id))
        except Exception as exception:
            logger.error(f"Failed to fetch participant events: {str(exception)}")
            raise ValueError(
                RepositoryError.PARTICIPANT_FETCH_FAILED.format(str(exception))
            )
