import logging
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import F

from backend.constants.messages import RepositoryError
from backend.models.conversation_member import ConversationMemberModel

logger = logging.getLogger(__name__)


class ConversationMemberRepository:
    @classmethod
    @transaction.atomic
    def upsert_member(
        cls,
        conversation_id,
        user_id,
        state: int,
        role: int,
        invited_by: str,
        now: datetime | None = None,
    ) -> tuple[ConversationMemberModel, bool]:
        """Idempotent membership; a re-add (e.g. after a decline) reactivates it."""
        now = now or datetime.now(timezone.utc)
        try:
            member, created = ConversationMemberModel.objects.update_or_create(
                conversation_id=conversation_id,
                user_id=user_id,
                defaults={
                    "state": state,
                    "role": role,
                    "invited_by": invited_by,
                    "left_at": None,
                    "is_deleted": False,
                },
                create_defaults={
                    "state": state,
                    "role": role,
                    "invited_by": invited_by,
                    "joined_at": now,
                    "is_deleted": False,
                    "created_by": invited_by,
                },
            )
            return member, created
        except Exception as exception:
            logger.error(f"Failed to upsert member: {str(exception)}")
            raise ValueError(
                RepositoryError.MEMBER_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def get_member(
        cls, conversation_id, user_id, for_update: bool = False
    ) -> ConversationMemberModel | None:
        try:
            queryset = ConversationMemberModel.objects.filter(
                conversation_id=conversation_id, user_id=user_id
            )
            if for_update:
                queryset = queryset.select_for_update()
            return queryset.first()
        except Exception as exception:
            logger.error(f"Failed to fetch member: {str(exception)}")
            raise ValueError(RepositoryError.MEMBER_FETCH_FAILED.format(str(exception)))

    @classmethod
    def get_active_member(
        cls, conversation_id, user_id
    ) -> ConversationMemberModel | None:
        """A member who has neither left nor been cleared (either PENDING/ACCEPTED)."""
        member = cls.get_member(conversation_id, user_id)
        if member is None or member.is_deleted or member.left_at is not None:
            return None
        return member

    @classmethod
    @transaction.atomic
    def increment_unread(cls, conversation_id, exclude_user_id, delta: int = 1) -> None:
        """Bump ``unread_count`` for every active member except the sender."""
        try:
            ConversationMemberModel.objects.filter(
                conversation_id=conversation_id,
                left_at__isnull=True,
                is_deleted=False,
            ).exclude(user_id=exclude_user_id).update(
                unread_count=F("unread_count") + delta
            )
        except Exception as exception:
            logger.error(f"Failed to increment unread: {str(exception)}")
            raise ValueError(
                RepositoryError.MEMBER_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def reset_unread(cls, conversation_id, user_id) -> None:
        """Clear the caller's unread counter for a conversation (mark read)."""
        try:
            ConversationMemberModel.objects.filter(
                conversation_id=conversation_id, user_id=user_id
            ).update(unread_count=0)
        except Exception as exception:
            logger.error(f"Failed to reset unread: {str(exception)}")
            raise ValueError(
                RepositoryError.MEMBER_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    def count_unread_conversations(cls, user_id) -> int:
        """How many active conversations have unread messages for the user —
        i.e. the number of people who messaged them that they haven't read."""
        try:
            return (
                ConversationMemberModel.objects.filter(
                    user_id=user_id,
                    unread_count__gt=0,
                    left_at__isnull=True,
                    is_deleted=False,
                )
                .exclude(conversation__is_deleted=True)
                .count()
            )
        except Exception as exception:
            logger.error(f"Failed to count unread: {str(exception)}")
            raise ValueError(RepositoryError.MEMBER_FETCH_FAILED.format(str(exception)))

    @classmethod
    def peers_for(cls, conversation_ids, exclude_user_id) -> dict:
        """Map each conversation id → its other active member's user (DIRECT peer).

        One query for a batch of conversations, avoiding N+1 in inbox listing.
        """
        try:
            rows = (
                ConversationMemberModel.objects.select_related("user")
                .filter(
                    conversation_id__in=list(conversation_ids),
                    left_at__isnull=True,
                    is_deleted=False,
                )
                .exclude(user_id=exclude_user_id)
            )
            return {row.conversation_id: row.user for row in rows}
        except Exception as exception:
            logger.error(f"Failed to fetch peers: {str(exception)}")
            raise ValueError(RepositoryError.MEMBER_FETCH_FAILED.format(str(exception)))

    @classmethod
    def list_active(cls, conversation_id) -> list[ConversationMemberModel]:
        try:
            return list(
                ConversationMemberModel.objects.select_related("user").filter(
                    conversation_id=conversation_id,
                    left_at__isnull=True,
                    is_deleted=False,
                )
            )
        except Exception as exception:
            logger.error(f"Failed to list members: {str(exception)}")
            raise ValueError(RepositoryError.MEMBER_FETCH_FAILED.format(str(exception)))

    @classmethod
    @transaction.atomic
    def set_state(
        cls, conversation_id, user_id, state: int
    ) -> ConversationMemberModel | None:
        try:
            member = (
                ConversationMemberModel.objects.select_for_update()
                .filter(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    is_deleted=False,
                    left_at__isnull=True,
                )
                .first()
            )
            if member is None:
                return None
            member.state = state
            member.save()
            return member
        except Exception as exception:
            logger.error(f"Failed to set member state: {str(exception)}")
            raise ValueError(
                RepositoryError.MEMBER_UPSERT_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def soft_delete(cls, conversation_id, user_id) -> ConversationMemberModel | None:
        try:
            member = (
                ConversationMemberModel.objects.select_for_update()
                .filter(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    is_deleted=False,
                )
                .first()
            )
            if member is None:
                return None
            member.is_deleted = True
            member.save()
            return member
        except Exception as exception:
            logger.error(f"Failed to soft-delete member: {str(exception)}")
            raise ValueError(
                RepositoryError.MEMBER_UPSERT_FAILED.format(str(exception))
            )
