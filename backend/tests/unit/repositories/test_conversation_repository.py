from datetime import timedelta

from django.test import TestCase

from backend.constants.chat import ConversationSection, MemberState
from backend.models.conversation import ConversationModel
from backend.repositories.conversation_repository import (
    ConversationRepository,
    direct_dm_key,
)
from backend.tests.factories import (
    NOW,
    create_conversation,
    create_member,
    create_user,
)

ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value


class GetOrCreateDirectTests(TestCase):
    def setUp(self):
        self.a = create_user()
        self.b = create_user()
        self.dm_key = direct_dm_key(self.a.id, self.b.id)

    def test_creates_direct_conversation(self):
        conversation, created = ConversationRepository.get_or_create_direct(
            dm_key=self.dm_key, created_by=str(self.a.id), now=NOW
        )

        self.assertTrue(created)
        self.assertEqual(conversation.dm_key, self.dm_key)
        self.assertEqual(conversation.type, ConversationModel.ConversationType.DIRECT)
        self.assertEqual(conversation.last_message_at, NOW)

    def test_is_idempotent_for_same_pair(self):
        first, created_first = ConversationRepository.get_or_create_direct(
            dm_key=self.dm_key, created_by=str(self.a.id), now=NOW
        )
        second, created_second = ConversationRepository.get_or_create_direct(
            dm_key=self.dm_key, created_by=str(self.b.id), now=NOW
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(ConversationModel.objects.count(), 1)

    def test_dm_key_is_order_independent(self):
        self.assertEqual(
            direct_dm_key(self.a.id, self.b.id),
            direct_dm_key(self.b.id, self.a.id),
        )


class TouchLastMessageTests(TestCase):
    def test_updates_preview_and_timestamp(self):
        conversation = create_conversation(created_by=str(create_user().id))
        later = NOW + timedelta(minutes=5)

        ConversationRepository.touch_last_message(
            conversation.id, at=later, preview="hey there"
        )

        conversation.refresh_from_db()
        self.assertEqual(conversation.last_message_at, later)
        self.assertEqual(conversation.last_message_preview, "hey there")

    def test_truncates_long_preview(self):
        conversation = create_conversation(created_by=str(create_user().id))

        ConversationRepository.touch_last_message(
            conversation.id, at=NOW, preview="x" * 400
        )

        conversation.refresh_from_db()
        self.assertEqual(len(conversation.last_message_preview), 300)


class ListForUserTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.peer = create_user()

    def _conv(self, minutes: int, state: int) -> ConversationModel:
        conversation = create_conversation(
            created_by=str(self.user.id),
            last_message_at=NOW + timedelta(minutes=minutes),
        )
        create_member(conversation, self.user, state=state)
        create_member(conversation, self.peer, state=ACCEPTED)
        return conversation

    def test_primary_returns_accepted_newest_first(self):
        older = self._conv(1, ACCEPTED)
        newer = self._conv(5, ACCEPTED)
        self._conv(3, PENDING)  # a request — excluded from primary

        members, next_cursor, has_more = ConversationRepository.list_for_user(
            user_id=str(self.user.id),
            section=ConversationSection.PRIMARY,
            limit=20,
        )

        self.assertEqual([m.conversation.id for m in members], [newer.id, older.id])
        self.assertFalse(has_more)
        self.assertIsNone(next_cursor)

    def test_requests_returns_only_pending(self):
        self._conv(1, ACCEPTED)
        pending = self._conv(2, PENDING)

        members, _, _ = ConversationRepository.list_for_user(
            user_id=str(self.user.id),
            section=ConversationSection.REQUESTS,
            limit=20,
        )

        self.assertEqual([m.conversation.id for m in members], [pending.id])

    def test_cursor_paginates(self):
        c3 = self._conv(3, ACCEPTED)
        c2 = self._conv(2, ACCEPTED)
        c1 = self._conv(1, ACCEPTED)

        page1, cursor1, more1 = ConversationRepository.list_for_user(
            user_id=str(self.user.id),
            section=ConversationSection.PRIMARY,
            limit=2,
        )
        self.assertEqual([m.conversation.id for m in page1], [c3.id, c2.id])
        self.assertTrue(more1)
        self.assertIsNotNone(cursor1)

        page2, _, more2 = ConversationRepository.list_for_user(
            user_id=str(self.user.id),
            section=ConversationSection.PRIMARY,
            limit=2,
            cursor=cursor1,
        )
        self.assertEqual([m.conversation.id for m in page2], [c1.id])
        self.assertFalse(more2)
