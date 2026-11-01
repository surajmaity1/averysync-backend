from datetime import datetime, timezone

from backend.constants.chat import MemberState, MessageType
from backend.dto.message_dto import MessageDTO
from backend.dto.responses.cursor_page import MessageListResponse
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    ConversationNotFoundException,
    NotConversationMemberException,
)
from backend.repositories.block_repository import BlockRepository
from backend.repositories.conversation_member_repository import (
    ConversationMemberRepository,
)
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.message_repository import MessageRepository

ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value
TEXT = MessageType.TEXT.value


class MessageService:
    @classmethod
    def _prepare_message_dto(cls, message) -> MessageDTO:
        return MessageDTO(
            id=message.id,
            conversationId=message.conversation_id,
            senderId=message.sender_id,
            type=message.type,
            body=None if message.is_deleted else message.body,
            metadata=message.metadata,
            isDeleted=message.is_deleted,
            createdAt=message.created_at,
        )

    @classmethod
    def _peer_id(cls, conversation_id, caller_id):
        for member in ConversationMemberRepository.list_active(conversation_id):
            if str(member.user_id) != str(caller_id):
                return member.user_id
        return None

    @classmethod
    def send(
        cls,
        caller_id: str,
        conversation_id,
        body: str,
        client_message_id: str | None = None,
        now: datetime | None = None,
    ) -> MessageDTO:
        now = now or datetime.now(timezone.utc)

        conversation = ConversationRepository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundException(str(conversation_id))

        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        if member is None:
            raise NotConversationMemberException(str(conversation_id))

        peer_id = cls._peer_id(conversation_id, caller_id)
        if peer_id is not None and BlockRepository.is_blocked(
            str(caller_id), str(peer_id)
        ):
            raise CannotMessageBlockedUserException(str(peer_id))

        message, created = MessageRepository.create(
            conversation_id=conversation_id,
            sender_id=caller_id,
            body=body,
            message_type=TEXT,
            client_message_id=client_message_id,
            now=now,
        )

        if created:
            ConversationRepository.touch_last_message(
                conversation_id, at=now, preview=body
            )
            # Unread fan-out: every other active member gains one unread (doc §6
            # step 7) — this is what drives the recipient's message-icon badge.
            ConversationMemberRepository.increment_unread(
                conversation_id, exclude_user_id=caller_id
            )
            # Implicit accept (doc C5): a recipient replying to a request
            # promotes their own membership PENDING → ACCEPTED.
            if member.state == PENDING:
                ConversationMemberRepository.set_state(
                    conversation_id, caller_id, ACCEPTED
                )

        return cls._prepare_message_dto(message)

    @classmethod
    def list_messages(
        cls,
        caller_id: str,
        conversation_id,
        limit: int,
        cursor: str | None = None,
    ) -> MessageListResponse:
        conversation = ConversationRepository.get_by_id(conversation_id)
        if conversation is None:
            raise ConversationNotFoundException(str(conversation_id))

        member = ConversationMemberRepository.get_active_member(
            conversation_id, caller_id
        )
        if member is None:
            raise NotConversationMemberException(str(conversation_id))

        rows, next_cursor, has_more = MessageRepository.list_by_conversation(
            conversation_id, limit=limit, cursor=cursor
        )
        data = [cls._prepare_message_dto(message) for message in rows]
        return MessageListResponse(data=data, nextCursor=next_cursor, hasMore=has_more)
