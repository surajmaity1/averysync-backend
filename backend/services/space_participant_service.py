import logging
from datetime import datetime, timedelta, timezone

from django.conf import settings

from backend.constants.participant import ParticipantAction, ParticipantRole
from backend.constants.post import PostType, SpaceStatus
from backend.dto.responses.get_participants_response import GetParticipantsResponse
from backend.dto.responses.join_space_response import JoinSpaceResponse
from backend.dto.space_participant_dto import MuteParticipantDTO, ParticipantDTO
from backend.exceptions.participant_exception import (
    ModerationForbiddenException,
    ParticipantNotFoundException,
    SelfMuteNotAllowedException,
    SpaceEndedException,
    SpaceNotLiveException,
)
from backend.exceptions.post_exception import SpaceNotFoundException
from backend.models.post import PostModel
from backend.models.space_participant import SpaceParticipantModel
from backend.repositories.post_repository import PostRepository
from backend.repositories.space_participant_event_repository import (
    SpaceParticipantEventRepository,
)
from backend.repositories.space_participant_repository import (
    SpaceParticipantRepository,
)
from backend.utils.sfu import Sfu
from backend.utils.stream import Stream

logger = logging.getLogger(__name__)

TOKEN_LIFETIME_SECONDS = 3600


class SpaceParticipantService:
    @classmethod
    def join(
        cls, space_id: str, user_id: str, now: datetime | None = None
    ) -> tuple[JoinSpaceResponse, bool]:
        now = now or datetime.now(timezone.utc)
        space = cls._get_live_space(space_id=space_id)

        role = (
            ParticipantRole.HOST
            if space.created_by == user_id
            else ParticipantRole.LISTENER
        )
        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=space_id,
            user_id=user_id,
            role=role.value,
            joined_at=now,
        )
        SpaceParticipantEventRepository.create(
            post_id=space_id,
            target_user_id=user_id,
            actor=user_id,
            action=ParticipantAction.JOIN.value,
        )

        token = cls._build_token(
            space_id=space_id, user_id=user_id, participant=participant, now=now
        )
        return (
            JoinSpaceResponse(
                data=cls._prepare_participant_dto(participant, now=now), token=token
            ),
            created,
        )

    @classmethod
    def ensure_active_participant(
        cls,
        space_id: str,
        user_id: str,
        created_by: str,
        now: datetime | None = None,
    ) -> SpaceParticipantModel:
        now = now or datetime.now(timezone.utc)
        role = (
            ParticipantRole.HOST if created_by == user_id else ParticipantRole.LISTENER
        )
        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=space_id,
            user_id=user_id,
            role=role.value,
            joined_at=now,
        )
        if created:
            SpaceParticipantEventRepository.create(
                post_id=space_id,
                target_user_id=user_id,
                actor=user_id,
                action=ParticipantAction.JOIN.value,
            )
        return participant

    @classmethod
    def get_participants(
        cls, space_id: str, include_left: bool = False, now: datetime | None = None
    ) -> GetParticipantsResponse:
        now = now or datetime.now(timezone.utc)
        cls._get_space(space_id=space_id)

        participants = SpaceParticipantRepository.list_by_post(
            post_id=space_id, include_left=include_left
        )
        return GetParticipantsResponse(
            data=[
                cls._prepare_participant_dto(participant, now=now)
                for participant in participants
            ]
        )

    @classmethod
    def leave_or_remove(
        cls,
        space_id: str,
        target_user_id: str,
        caller_id: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)
        space = cls._get_live_space(space_id=space_id)

        is_self_leave = target_user_id == caller_id
        if not is_self_leave:
            cls._ensure_caller_is_host(space=space, caller_id=caller_id)

        marked_left = SpaceParticipantRepository.mark_left(
            post_id=space_id, user_id=target_user_id, left_at=now
        )
        if marked_left is None:
            raise ParticipantNotFoundException(
                user_id=target_user_id, space_id=space_id
            )

        SpaceParticipantEventRepository.create(
            post_id=space_id,
            target_user_id=target_user_id,
            actor=caller_id,
            action=(
                ParticipantAction.LEAVE.value
                if is_self_leave
                else ParticipantAction.REMOVE.value
            ),
        )

    @classmethod
    def set_mute_state(
        cls,
        space_id: str,
        target_user_id: str,
        caller_id: str,
        dto: MuteParticipantDTO,
        now: datetime | None = None,
    ) -> ParticipantDTO:
        now = now or datetime.now(timezone.utc)
        space = cls._get_live_space(space_id=space_id)

        if dto.isMuted and target_user_id == caller_id:
            raise SelfMuteNotAllowedException()

        cls._ensure_caller_is_host(space=space, caller_id=caller_id)

        target = SpaceParticipantRepository.get_active(
            post_id=space_id, user_id=target_user_id
        )
        if target is None:
            raise ParticipantNotFoundException(
                user_id=target_user_id, space_id=space_id
            )

        if dto.isMuted:
            updated = cls._apply_mute(
                space=space,
                space_id=space_id,
                target_user_id=target_user_id,
                caller_id=caller_id,
                dto=dto,
                now=now,
            )
        else:
            updated = cls._apply_unmute(
                space_id=space_id,
                target_user_id=target_user_id,
                caller_id=caller_id,
                target=target,
                now=now,
            )

        if updated is None:
            raise ParticipantNotFoundException(
                user_id=target_user_id, space_id=space_id
            )

        result = cls._prepare_participant_dto(updated, now=now)
        cls._notify_sfu(
            space_id=space_id, target_user_id=target_user_id, participant=result
        )
        return result

    @classmethod
    def _notify_sfu(
        cls, space_id: str, target_user_id: str, participant: ParticipantDTO
    ) -> None:
        muted_until = (
            int(participant.mutedUntil.timestamp())
            if participant.mutedUntil is not None
            else None
        )
        try:
            Sfu.push_mute(
                space_id=space_id,
                user_id=target_user_id,
                is_muted=participant.isMuted,
                muted_until=muted_until,
            )
        except Exception:
            logger.exception(
                "Failed to push mute state to SFU (space=%s, user=%s)",
                space_id,
                target_user_id,
            )

    @classmethod
    def _apply_mute(
        cls,
        space: PostModel,
        space_id: str,
        target_user_id: str,
        caller_id: str,
        dto: MuteParticipantDTO,
        now: datetime,
    ) -> SpaceParticipantModel | None:
        if dto.durationSeconds is not None:
            muted_until = now + timedelta(seconds=dto.durationSeconds)
        else:
            muted_until = space.scheduled_ended_at

        updated = SpaceParticipantRepository.set_mute(
            post_id=space_id,
            user_id=target_user_id,
            muted_until=muted_until,
            muted_by=caller_id,
            muted_at=now,
        )
        if updated is not None:
            SpaceParticipantEventRepository.create(
                post_id=space_id,
                target_user_id=target_user_id,
                actor=caller_id,
                action=ParticipantAction.MUTE.value,
                reason=dto.reason,
                muted_until=muted_until,
            )
        return updated

    @classmethod
    def _apply_unmute(
        cls,
        space_id: str,
        target_user_id: str,
        caller_id: str,
        target: SpaceParticipantModel,
        now: datetime,
    ) -> SpaceParticipantModel | None:
        was_effectively_muted, _ = cls._effective_mute(target, now=now)

        updated = SpaceParticipantRepository.clear_mute(
            post_id=space_id, user_id=target_user_id
        )
        if updated is not None and was_effectively_muted:
            SpaceParticipantEventRepository.create(
                post_id=space_id,
                target_user_id=target_user_id,
                actor=caller_id,
                action=ParticipantAction.UNMUTE.value,
                reason=None,
                muted_until=None,
            )
        return updated

    @classmethod
    def effective_mute_claims(
        cls, space_id: str, user_id: str, now: datetime | None = None
    ) -> tuple[bool, int | None]:
        now = now or datetime.now(timezone.utc)
        participant = SpaceParticipantRepository.get_active(
            post_id=space_id, user_id=user_id
        )
        if participant is None:
            return False, None
        is_muted, muted_until = cls._effective_mute(participant, now=now)
        return is_muted, int(muted_until.timestamp()) if muted_until else None

    @classmethod
    def _get_space(cls, space_id: str) -> PostModel:
        try:
            space = PostRepository.get_by_id(post_id=space_id)
        except ValueError as exception:
            raise SpaceNotFoundException(space_id=space_id) from exception

        if space is None or space.type != PostType.SPACE.name:
            raise SpaceNotFoundException(space_id=space_id)
        return space

    @classmethod
    def _get_live_space(cls, space_id: str) -> PostModel:
        space = cls._get_space(space_id=space_id)

        if space.status == SpaceStatus.SCHEDULED.value:
            raise SpaceNotLiveException(space_id=space_id)
        if space.status in (SpaceStatus.ENDED.value, SpaceStatus.CLOSED.value):
            raise SpaceEndedException(space_id=space_id)
        return space

    @classmethod
    def _ensure_caller_is_host(cls, space: PostModel, caller_id: str) -> None:
        if space.created_by == caller_id:
            return

        caller = SpaceParticipantRepository.get_active(
            post_id=str(space.id), user_id=caller_id
        )
        if caller is None or caller.role != ParticipantRole.HOST.value:
            raise ModerationForbiddenException(space_id=str(space.id))

    @classmethod
    def _effective_mute(
        cls, participant: SpaceParticipantModel, now: datetime
    ) -> tuple[bool, datetime | None]:
        is_muted = participant.is_muted and (
            participant.muted_until is None or participant.muted_until > now
        )
        return is_muted, participant.muted_until if is_muted else None

    @classmethod
    def _prepare_participant_dto(
        cls, participant: SpaceParticipantModel, now: datetime
    ) -> ParticipantDTO:
        is_muted, muted_until = cls._effective_mute(participant, now=now)
        return ParticipantDTO(
            id=participant.id,
            spaceId=participant.post_id,
            userId=participant.user_id,
            role=participant.role,
            isMuted=is_muted,
            mutedUntil=muted_until,
            firstJoinedAt=participant.first_joined_at,
            lastJoinedAt=participant.last_joined_at,
            leftAt=participant.left_at,
        )

    @classmethod
    def _build_token(
        cls,
        space_id: str,
        user_id: str,
        participant: SpaceParticipantModel,
        now: datetime,
    ) -> str:
        role_name = ParticipantRole(participant.role).name
        is_muted, muted_until = cls._effective_mute(participant, now=now)
        payload = {
            "user_id": str(user_id),
            "username": str(user_id),
            "room_id": str(space_id),
            "role": role_name,
            "is_host": role_name == ParticipantRole.HOST.name,
            "is_muted": is_muted,
            "muted_until": int(muted_until.timestamp()) if muted_until else None,
            "iss": getattr(settings, "WEBRTC_ISSUER"),
            "aud": getattr(settings, "WEBRTC_AUDIENCE"),
            "exp": int(now.timestamp()) + TOKEN_LIFETIME_SECONDS,
        }
        return Stream.stream_voice_peer_to_peer(payload=payload)
