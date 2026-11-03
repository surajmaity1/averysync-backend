import logging
from datetime import datetime, timezone

from django.db import models, transaction

from backend.constants.chat import ConversationSection, ConversationType, MemberState
from backend.constants.messages import RepositoryError
from backend.models.conversation import ConversationModel
from backend.models.conversation_member import ConversationMemberModel
from backend.utils.cursor import decode_cursor, encode_cursor

logger = logging.getLogger(__name__)

DIRECT = ConversationType.DIRECT.value
ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value


def direct_dm_key(user_a, user_b) -> str:
    return ":".join(sorted([str(user_a), str(user_b)]))


class ConversationRepository:
    @classmethod
    @transaction.atomic
    def get_or_create_direct(
        cls, dm_key: str, created_by: str, now: datetime | None = None
    ) -> tuple[ConversationModel, bool]:
        now = now or datetime.now(timezone.utc)
        try:
            conversation, created = ConversationModel.objects.get_or_create(
                dm_key=dm_key,
                type=DIRECT,
                is_deleted=False,
                defaults={
                    "created_by": created_by,
                    "last_message_at": now,
                },
            )
            return conversation, created
        except Exception as exception:
            logger.error(f"Failed to upsert conversation: {str(exception)}")
            raise ValueError(
                RepositoryError.CONVERSATION_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def get_by_id(cls, conversation_id) -> ConversationModel | None:
        try:
            return ConversationModel.objects.filter(
                id=conversation_id, is_deleted=False
            ).first()
        except Exception as exception:
            logger.error(f"Failed to fetch conversation: {str(exception)}")
            raise ValueError(
                RepositoryError.CONVERSATION_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def touch_last_message(cls, conversation_id, at: datetime, preview: str) -> None:
        try:
            ConversationModel.objects.filter(id=conversation_id).update(
                last_message_at=at,
                last_message_preview=preview[:300],
                updated_at=at,
            )
        except Exception as exception:
            logger.error(f"Failed to touch conversation: {str(exception)}")
            raise ValueError(
                RepositoryError.CONVERSATION_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def list_for_user(
        cls,
        user_id: str,
        section: ConversationSection,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[ConversationMemberModel], str | None, bool]:
        """The caller's memberships for a section, newest-activity first.

        Returns ``(members, next_cursor, has_more)`` — each member carries its
        ``conversation`` (select_related) for summary building.
        """
        try:
            state = ACCEPTED if section == ConversationSection.PRIMARY else PENDING
            queryset = (
                ConversationMemberModel.objects.select_related("conversation")
                .filter(
                    user_id=user_id,
                    state=state,
                    left_at__isnull=True,
                    is_deleted=False,
                    conversation__is_deleted=False,
                )
                .order_by("-conversation__last_message_at", "-conversation__id")
            )

            if cursor:
                at, conv_id = decode_cursor(cursor)
                queryset = queryset.filter(
                    models.Q(conversation__last_message_at__lt=at)
                    | models.Q(
                        conversation__last_message_at=at,
                        conversation__id__lt=conv_id,
                    )
                )

            rows = list(queryset[: limit + 1])
            has_more = len(rows) > limit
            rows = rows[:limit]
            next_cursor = None
            if has_more and rows:
                last = rows[-1].conversation
                next_cursor = encode_cursor(last.last_message_at, last.id)
            return rows, next_cursor, has_more
        except ValueError:
            raise
        except Exception as exception:
            logger.error(f"Failed to list conversations: {str(exception)}")
            raise ValueError(
                RepositoryError.CONVERSATION_FETCH_FAILED.format(str(exception))
            )
