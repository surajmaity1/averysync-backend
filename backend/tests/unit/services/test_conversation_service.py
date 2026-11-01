import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.constants.chat import ConversationSection, MemberState
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    CannotMessageSelfException,
    ConversationNotFoundException,
    ConversationRequestNotFoundException,
    NotConversationMemberException,
)
from backend.services.conversation_service import ConversationService

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value

SP = "backend.services.conversation_service"


def _user(**overrides):
    defaults = {"id": uuid.uuid4(), "name": "Peer", "image": None}
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _conversation(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "type": 1,
        "title": None,
        "last_message_preview": None,
        "last_message_at": NOW,
        "is_deleted": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _member(conversation, state=ACCEPTED, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "conversation": conversation,
        "conversation_id": conversation.id,
        "state": state,
        "unread_count": 0,
        "user_id": uuid.uuid4(),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class CreateOrGetDirectTests(SimpleTestCase):
    def setUp(self):
        self.caller_id = str(uuid.uuid4())
        self.participant = _user()
        self.participant_id = str(self.participant.id)

        patchers = {
            "is_blocked": patch(f"{SP}.BlockRepository.is_blocked"),
            "get_user": patch(f"{SP}.UserRepository.get_by_id"),
            "get_or_create": patch(f"{SP}.ConversationRepository.get_or_create_direct"),
            "upsert": patch(f"{SP}.ConversationMemberRepository.upsert_member"),
            "active": patch(f"{SP}.ConversationMemberRepository.get_active_member"),
            "exists_accepted": patch(f"{SP}.FollowRepository.exists_accepted"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

        self.conversation = _conversation()
        self.mocks["is_blocked"].return_value = False
        self.mocks["get_user"].return_value = self.participant
        self.mocks["get_or_create"].return_value = (self.conversation, True)
        self.mocks["upsert"].return_value = (
            _member(self.conversation, state=ACCEPTED),
            True,
        )
        self.mocks["active"].return_value = None  # peer is new

    def test_self_dm_raises(self):
        with self.assertRaises(CannotMessageSelfException):
            ConversationService.create_or_get_direct(
                self.caller_id, self.caller_id, now=NOW
            )

    def test_blocked_pair_raises_non_disclosing(self):
        self.mocks["is_blocked"].return_value = True

        with self.assertRaises(CannotMessageBlockedUserException):
            ConversationService.create_or_get_direct(
                self.caller_id, self.participant_id, now=NOW
            )

    def test_public_peer_is_accepted(self):
        self.mocks["exists_accepted"].return_value = True

        dto, created = ConversationService.create_or_get_direct(
            self.caller_id, self.participant_id, now=NOW
        )

        self.assertTrue(created)
        self.assertEqual(dto.state, "ACCEPTED")
        # peer membership upserted as ACCEPTED
        peer_call = self.mocks["upsert"].call_args_list[-1]
        self.assertEqual(peer_call.kwargs["state"], ACCEPTED)

    def test_non_follower_peer_is_pending(self):
        self.mocks["exists_accepted"].return_value = False

        ConversationService.create_or_get_direct(
            self.caller_id, self.participant_id, now=NOW
        )

        peer_call = self.mocks["upsert"].call_args_list[-1]
        self.assertEqual(peer_call.kwargs["state"], PENDING)

    def test_existing_peer_is_not_rerouted(self):
        self.mocks["active"].return_value = _member(self.conversation, state=ACCEPTED)

        ConversationService.create_or_get_direct(
            self.caller_id, self.participant_id, now=NOW
        )

        # Only the caller's membership is upserted; peer left untouched.
        self.assertEqual(self.mocks["upsert"].call_count, 1)
        self.mocks["exists_accepted"].assert_not_called()


class ConversationReadWriteTests(SimpleTestCase):
    def setUp(self):
        self.caller_id = str(uuid.uuid4())
        self.conversation = _conversation()

        patchers = {
            "get_by_id": patch(f"{SP}.ConversationRepository.get_by_id"),
            "active": patch(f"{SP}.ConversationMemberRepository.get_active_member"),
            "set_state": patch(f"{SP}.ConversationMemberRepository.set_state"),
            "soft_delete": patch(f"{SP}.ConversationMemberRepository.soft_delete"),
            "reset_unread": patch(f"{SP}.ConversationMemberRepository.reset_unread"),
            "count_unread": patch(
                f"{SP}.ConversationMemberRepository.count_unread_conversations"
            ),
            "peers_for": patch(f"{SP}.ConversationMemberRepository.peers_for"),
            "list_for_user": patch(f"{SP}.ConversationRepository.list_for_user"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        self.mocks["peers_for"].return_value = {self.conversation.id: _user()}

    def test_detail_missing_conversation_raises_404(self):
        self.mocks["get_by_id"].return_value = None

        with self.assertRaises(ConversationNotFoundException):
            ConversationService.detail(self.caller_id, self.conversation.id)

    def test_detail_non_member_raises_403(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = None

        with self.assertRaises(NotConversationMemberException):
            ConversationService.detail(self.caller_id, self.conversation.id)

    def test_detail_ok(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = _member(self.conversation, state=ACCEPTED)

        dto = ConversationService.detail(self.caller_id, self.conversation.id)

        self.assertEqual(dto.id, self.conversation.id)
        self.assertEqual(dto.state, "ACCEPTED")

    def test_accept_without_pending_raises_404(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = _member(self.conversation, state=ACCEPTED)

        with self.assertRaises(ConversationRequestNotFoundException):
            ConversationService.accept(self.caller_id, self.conversation.id)

    def test_accept_promotes_pending(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].side_effect = [
            _member(self.conversation, state=PENDING),
            _member(self.conversation, state=ACCEPTED),
        ]

        dto = ConversationService.accept(self.caller_id, self.conversation.id)

        self.mocks["set_state"].assert_called_once()
        self.assertEqual(dto.state, "ACCEPTED")

    def test_decline_soft_deletes_pending(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = _member(self.conversation, state=PENDING)

        result = ConversationService.decline(self.caller_id, self.conversation.id)

        self.assertIsNone(result)
        self.mocks["soft_delete"].assert_called_once()

    def test_list_builds_summaries(self):
        member = _member(self.conversation, state=ACCEPTED)
        self.mocks["list_for_user"].return_value = ([member], "cursor-x", True)

        response = ConversationService.list(
            self.caller_id, ConversationSection.PRIMARY, limit=20
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.nextCursor, "cursor-x")
        self.assertTrue(response.hasMore)

    def test_mark_read_requires_membership(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = None

        with self.assertRaises(NotConversationMemberException):
            ConversationService.mark_read(self.caller_id, self.conversation.id)

        self.mocks["reset_unread"].assert_not_called()

    def test_mark_read_resets_the_caller_counter(self):
        self.mocks["get_by_id"].return_value = self.conversation
        self.mocks["active"].return_value = _member(self.conversation, state=ACCEPTED)

        ConversationService.mark_read(self.caller_id, self.conversation.id)

        self.mocks["reset_unread"].assert_called_once_with(
            self.conversation.id, self.caller_id
        )

    def test_unread_count_delegates_to_repository(self):
        self.mocks["count_unread"].return_value = 4

        self.assertEqual(
            ConversationService.unread_conversations_count(self.caller_id), 4
        )
