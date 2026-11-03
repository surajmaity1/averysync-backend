import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.constants.chat import MemberState
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    ConversationNotFoundException,
    NotConversationMemberException,
)
from backend.services.message_service import MessageService

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value

SP = "backend.services.message_service"


def _message(conversation_id, sender_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "type": 1,
        "body": "hey there",
        "metadata": None,
        "is_deleted": False,
        "created_at": NOW,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _member(state=ACCEPTED, user_id=None):
    return SimpleNamespace(state=state, user_id=user_id or uuid.uuid4())


class SendMessageTests(SimpleTestCase):
    def setUp(self):
        self.caller_id = str(uuid.uuid4())
        self.peer_id = uuid.uuid4()
        self.conversation_id = uuid.uuid4()

        patchers = {
            "get_by_id": patch(f"{SP}.ConversationRepository.get_by_id"),
            "touch": patch(f"{SP}.ConversationRepository.touch_last_message"),
            "active": patch(f"{SP}.ConversationMemberRepository.get_active_member"),
            "list_active": patch(f"{SP}.ConversationMemberRepository.list_active"),
            "set_state": patch(f"{SP}.ConversationMemberRepository.set_state"),
            "increment_unread": patch(
                f"{SP}.ConversationMemberRepository.increment_unread"
            ),
            "create": patch(f"{SP}.MessageRepository.create"),
            "is_blocked": patch(f"{SP}.BlockRepository.is_blocked"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

        self.mocks["get_by_id"].return_value = SimpleNamespace(id=self.conversation_id)
        self.mocks["active"].return_value = _member(state=ACCEPTED)
        self.mocks["list_active"].return_value = [
            _member(user_id=uuid.UUID(self.caller_id)),
            _member(user_id=self.peer_id),
        ]
        self.mocks["is_blocked"].return_value = False
        self.mocks["create"].return_value = (
            _message(self.conversation_id, self.caller_id),
            True,
        )

    def test_missing_conversation_raises_404(self):
        self.mocks["get_by_id"].return_value = None

        with self.assertRaises(ConversationNotFoundException):
            MessageService.send(self.caller_id, self.conversation_id, "hi", now=NOW)

    def test_non_member_raises_403(self):
        self.mocks["active"].return_value = None

        with self.assertRaises(NotConversationMemberException):
            MessageService.send(self.caller_id, self.conversation_id, "hi", now=NOW)

    def test_blocked_peer_raises_404(self):
        self.mocks["is_blocked"].return_value = True

        with self.assertRaises(CannotMessageBlockedUserException):
            MessageService.send(self.caller_id, self.conversation_id, "hi", now=NOW)

    def test_send_touches_conversation(self):
        dto = MessageService.send(self.caller_id, self.conversation_id, "hey", now=NOW)

        self.assertEqual(dto.body, "hey there")
        self.mocks["touch"].assert_called_once()

    def test_send_fans_out_unread_to_recipients(self):
        MessageService.send(self.caller_id, self.conversation_id, "hey", now=NOW)

        self.mocks["increment_unread"].assert_called_once_with(
            self.conversation_id, exclude_user_id=self.caller_id
        )

    def test_idempotent_resend_does_not_fan_out_again(self):
        self.mocks["create"].return_value = (
            _message(self.conversation_id, self.caller_id),
            False,
        )

        MessageService.send(
            self.caller_id,
            self.conversation_id,
            "hey",
            client_message_id="c-1",
            now=NOW,
        )

        self.mocks["increment_unread"].assert_not_called()

    def test_reply_to_request_implicitly_accepts(self):
        self.mocks["active"].return_value = _member(state=PENDING)

        MessageService.send(self.caller_id, self.conversation_id, "hey", now=NOW)

        self.mocks["set_state"].assert_called_once()

    def test_idempotent_resend_does_not_touch_again(self):
        self.mocks["create"].return_value = (
            _message(self.conversation_id, self.caller_id),
            False,  # duplicate clientMessageId
        )

        MessageService.send(
            self.caller_id,
            self.conversation_id,
            "hey",
            client_message_id="c-1",
            now=NOW,
        )

        self.mocks["touch"].assert_not_called()


class ListMessagesTests(SimpleTestCase):
    def setUp(self):
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

        patchers = {
            "get_by_id": patch(f"{SP}.ConversationRepository.get_by_id"),
            "active": patch(f"{SP}.ConversationMemberRepository.get_active_member"),
            "list": patch(f"{SP}.MessageRepository.list_by_conversation"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        self.mocks["get_by_id"].return_value = SimpleNamespace(id=self.conversation_id)
        self.mocks["active"].return_value = _member(state=ACCEPTED)

    def test_non_member_raises_403(self):
        self.mocks["active"].return_value = None

        with self.assertRaises(NotConversationMemberException):
            MessageService.list_messages(self.caller_id, self.conversation_id, limit=20)

    def test_returns_mapped_messages(self):
        self.mocks["list"].return_value = (
            [_message(self.conversation_id, self.caller_id)],
            "cursor-y",
            True,
        )

        response = MessageService.list_messages(
            self.caller_id, self.conversation_id, limit=20
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.nextCursor, "cursor-y")

    def test_tombstoned_message_hides_body(self):
        self.mocks["list"].return_value = (
            [_message(self.conversation_id, self.caller_id, is_deleted=True)],
            None,
            False,
        )

        response = MessageService.list_messages(
            self.caller_id, self.conversation_id, limit=20
        )

        self.assertIsNone(response.data[0].body)
        self.assertTrue(response.data[0].isDeleted)
