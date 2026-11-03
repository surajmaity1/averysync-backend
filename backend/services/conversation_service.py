from datetime import datetime, timezone

from backend.constants.chat import (
    ConversationSection,
    MemberRole,
    MemberState,
)
from backend.dto.conversation_dto import (
    ConversationDetailDTO,
    ConversationPeerDTO,
    ConversationSummaryDTO,
)
from backend.dto.responses.cursor_page import ConversationListResponse
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    CannotMessageSelfException,
    ConversationNotFoundException,
    ConversationRequestNotFoundException,
    NotConversationMemberException,
)
from backend.repositories.block_repository import BlockRepository
from backend.repositories.conversation_member_repository import (
    ConversationMemberRepository,
)
from backend.repositories.conversation_repository import (
    ConversationRepository,
    direct_dm_key,
)
from backend.repositories.follow_repository import FollowRepository
from backend.repositories.user_repositories import UserRepository

ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value
MEMBER = MemberRole.MEMBER.value


class ConversationService:
    @classmethod
    def _prepare_peer(cls, user) -> ConversationPeerDTO | None:
        if user is None:
            return None
        return ConversationPeerDTO(id=user.id, name=user.name, image=user.image)

    @classmethod
    def _prepare_summary(cls, member, peer_user, cls_dto=ConversationSummaryDTO):
        conversation = member.conversation
        return cls_dto(
            id=conversation.id,
            type=conversation.type,
            peer=cls._prepare_peer(peer_user),
            title=conversation.title,
            state=member.state,
            lastMessagePreview=conversation.last_message_preview,
            lastMessageAt=conversation.last_message_at,
            unreadCount=member.unread_count,
        )

    @classmethod
    def create_or_get_direct(
        cls, caller_id: str, participant_id: str, now: datetime | None = None
    ) -> tuple[ConversationDetailDTO, bool]:
        now = now or datetime.now(timezone.utc)
        if str(caller_id) == str(participant_id):
            raise CannotMessageSelfException()

        if BlockRepository.is_blocked(str(caller_id), str(participant_id)):
            raise CannotMessageBlockedUserException(str(participant_id))

        # Validates existence (raises UserNotFoundException → 404, non-disclosing).
        participant = UserRepository.get_by_id(participant_id)

        dm_key = direct_dm_key(caller_id, participant_id)
        conversation, created = ConversationRepository.get_or_create_direct(
            dm_key=dm_key, created_by=str(caller_id), now=now
        )

        # Caller (initiator) is always ACCEPTED; opening an inbound request here
        # is an implicit accept.
        caller_member, _ = ConversationMemberRepository.upsert_member(
            conversation_id=conversation.id,
            user_id=caller_id,
            state=ACCEPTED,
            role=MEMBER,
            invited_by=str(caller_id),
            now=now,
        )

        # Only route a *new* peer membership; never downgrade an existing one.
        peer_member = ConversationMemberRepository.get_active_member(
            conversation.id, participant_id
        )
        if peer_member is None:
            peer_state = (
                ACCEPTED
                if FollowRepository.exists_accepted(
                    follower_id=str(participant_id), followee_id=str(caller_id)
                )
                else PENDING
            )
            ConversationMemberRepository.upsert_member(
                conversation_id=conversation.id,
                user_id=participant_id,
                state=peer_state,
                role=MEMBER,
                invited_by=str(caller_id),
                now=now,
            )

        caller_member.conversation = conversation
        return (
            cls._prepare_summary(caller_member, participant, ConversationDetailDTO),
            created,
        )

    @classmethod
    def list(
        cls,
        caller_id: str,
        section: ConversationSection,
        limit: int,
        cursor: str | None = None,
    ) -> ConversationListResponse:
        members, next_cursor, has_more = ConversationRepository.list_for_user(
            user_id=str(caller_id), section=section, limit=limit, cursor=cursor
        )
        peer_by_conv = ConversationMemberRepository.peers_for(
            [m.conversation_id for m in members], exclude_user_id=caller_id
        )
        data = [
            cls._prepare_summary(member, peer_by_conv.get(member.conversation_id))
            for member in members
        ]
        return ConversationListResponse(
            data=data, nextCursor=next_cursor, hasMore=has_more
        )

    @classmethod
    def _member_or_403(cls, caller_id: str, conversation_id):
        conversation = ConversationRepository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundException(str(conversation_id))
        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        if member is None:
            raise NotConversationMemberException(str(conversation_id))
        member.conversation = conversation
        return member

    @classmethod
    def detail(cls, caller_id: str, conversation_id) -> ConversationDetailDTO:
        member = cls._member_or_403(caller_id, conversation_id)
        peer_by_conv = ConversationMemberRepository.peers_for(
            [conversation_id], exclude_user_id=caller_id
        )
        return cls._prepare_summary(
            member, peer_by_conv.get(member.conversation_id), ConversationDetailDTO
        )

    @classmethod
    def accept(cls, caller_id: str, conversation_id) -> ConversationDetailDTO:
        conversation = ConversationRepository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundException(str(conversation_id))
        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        if member is None or member.state != PENDING:
            raise ConversationRequestNotFoundException(str(conversation_id))

        ConversationMemberRepository.set_state(conversation_id, caller_id, ACCEPTED)
        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        member.conversation = conversation
        peer_by_conv = ConversationMemberRepository.peers_for(
            [conversation_id], exclude_user_id=caller_id
        )
        return cls._prepare_summary(
            member, peer_by_conv.get(member.conversation_id), ConversationDetailDTO
        )

    @classmethod
    def decline(cls, caller_id: str, conversation_id) -> None:
        conversation = ConversationRepository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundException(str(conversation_id))
        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        if member is None or member.state != PENDING:
            raise ConversationRequestNotFoundException(str(conversation_id))

        ConversationMemberRepository.soft_delete(conversation_id, caller_id)
        return None

    @classmethod
    def mark_read(cls, caller_id: str, conversation_id) -> None:
        """Clear the caller's unread counter for a conversation. Member-guarded
        (403 if not an active member) — idempotent."""
        cls._member_or_403(caller_id, conversation_id)
        ConversationMemberRepository.reset_unread(conversation_id, caller_id)
        return None

    @classmethod
    def unread_conversations_count(cls, caller_id: str) -> int:
        """Number of conversations with unread messages — the message-icon badge
        count (one per person who messaged the caller)."""
        return ConversationMemberRepository.count_unread_conversations(caller_id)
