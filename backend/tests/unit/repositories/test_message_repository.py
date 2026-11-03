from datetime import timedelta

from django.test import TestCase

from backend.models.message import MessageModel
from backend.repositories.message_repository import MessageRepository
from backend.tests.factories import (
    NOW,
    create_conversation,
    create_message,
    create_user,
)


class CreateMessageTests(TestCase):
    def setUp(self):
        self.sender = create_user()
        self.conversation = create_conversation(created_by=str(self.sender.id))

    def test_creates_text_message(self):
        message, created = MessageRepository.create(
            conversation_id=self.conversation.id,
            sender_id=self.sender.id,
            body="hey there",
            now=NOW,
        )

        self.assertTrue(created)
        self.assertEqual(message.body, "hey there")
        self.assertEqual(message.created_by, str(self.sender.id))

    def test_is_idempotent_on_client_message_id(self):
        first, created_first = MessageRepository.create(
            conversation_id=self.conversation.id,
            sender_id=self.sender.id,
            body="hey",
            client_message_id="c-1",
        )
        second, created_second = MessageRepository.create(
            conversation_id=self.conversation.id,
            sender_id=self.sender.id,
            body="hey again",
            client_message_id="c-1",
        )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.body, "hey")
        self.assertEqual(MessageModel.objects.count(), 1)


class ListMessagesTests(TestCase):
    def setUp(self):
        self.sender = create_user()
        self.conversation = create_conversation(created_by=str(self.sender.id))

    def _message(self, minutes: int) -> MessageModel:
        return create_message(
            self.conversation, self.sender, created_at=NOW + timedelta(minutes=minutes)
        )

    def test_returns_newest_first(self):
        m1 = self._message(1)
        m2 = self._message(2)
        m3 = self._message(3)

        rows, next_cursor, has_more = MessageRepository.list_by_conversation(
            self.conversation.id, limit=20
        )

        self.assertEqual([m.id for m in rows], [m3.id, m2.id, m1.id])
        self.assertFalse(has_more)
        self.assertIsNone(next_cursor)

    def test_cursor_paginates_history(self):
        m1 = self._message(1)
        m2 = self._message(2)
        m3 = self._message(3)

        page1, cursor1, more1 = MessageRepository.list_by_conversation(
            self.conversation.id, limit=2
        )
        self.assertEqual([m.id for m in page1], [m3.id, m2.id])
        self.assertTrue(more1)

        page2, _, more2 = MessageRepository.list_by_conversation(
            self.conversation.id, limit=2, cursor=cursor1
        )
        self.assertEqual([m.id for m in page2], [m1.id])
        self.assertFalse(more2)
