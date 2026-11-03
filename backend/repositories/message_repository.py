import logging
from datetime import datetime, timezone

from django.db import models, transaction

from backend.constants.chat import MessageType
from backend.constants.messages import RepositoryError
from backend.models.message import MessageModel
from backend.utils.cursor import decode_cursor, encode_cursor

logger = logging.getLogger(__name__)

TEXT = MessageType.TEXT.value


class MessageRepository:
    @classmethod
    @transaction.atomic
    def create(
        cls,
        conversation_id,
        sender_id,
        body: str,
        message_type: int = TEXT,
        client_message_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[MessageModel, bool]:
        """Insert a message. Idempotent on ``client_message_id`` — a duplicate
        returns the original row with ``created=False`` (doc C7)."""
        now = now or datetime.now(timezone.utc)
        try:
            if client_message_id:
                existing = MessageModel.objects.filter(
                    conversation_id=conversation_id,
                    sender_id=sender_id,
                    client_message_id=client_message_id,
                ).first()
                if existing is not None:
                    return existing, False

            message = MessageModel.objects.create(
                conversation_id=conversation_id,
                sender_id=sender_id,
                type=message_type,
                body=body,
                client_message_id=client_message_id,
                created_at=now,
                created_by=str(sender_id),
            )
            return message, True
        except Exception as exception:
            logger.error(f"Failed to create message: {str(exception)}")
            raise ValueError(
                RepositoryError.MESSAGE_CREATE_FAILED.format(str(exception))
            )

    @classmethod
    def get_latest(cls, conversation_id) -> MessageModel | None:
        try:
            return (
                MessageModel.objects.filter(conversation_id=conversation_id)
                .order_by("-created_at", "-id")
                .first()
            )
        except Exception as exception:
            logger.error(f"Failed to fetch message: {str(exception)}")
            raise ValueError(
                RepositoryError.MESSAGE_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    def list_by_conversation(
        cls, conversation_id, limit: int, cursor: str | None = None
    ) -> tuple[list[MessageModel], str | None, bool]:
        """Newest-first history, keyset-paginated on ``(created_at, id)``."""
        try:
            queryset = MessageModel.objects.filter(
                conversation_id=conversation_id
            ).order_by("-created_at", "-id")

            if cursor:
                at, message_id = decode_cursor(cursor)
                queryset = queryset.filter(
                    models.Q(created_at__lt=at)
                    | models.Q(created_at=at, id__lt=message_id)
                )

            rows = list(queryset[: limit + 1])
            has_more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = None
            if has_more and rows:
                last = rows[-1]
                next_cursor = encode_cursor(last.created_at, last.id)
            return rows, next_cursor, has_more
        except ValueError:
            raise
        except Exception as exception:
            logger.error(f"Failed to list messages: {str(exception)}")
            raise ValueError(
                RepositoryError.MESSAGE_FETCH_FAILED.format(str(exception))
            )
