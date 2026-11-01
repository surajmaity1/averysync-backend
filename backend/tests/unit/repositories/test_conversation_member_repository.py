from django.test import TestCase

from backend.constants.chat import MemberRole, MemberState
from backend.models.conversation_member import ConversationMemberModel
from backend.repositories.conversation_member_repository import (
    ConversationMemberRepository,
)
from backend.tests.factories import NOW, create_conversation, create_member, create_user

ACCEPTED = MemberState.ACCEPTED.value
PENDING = MemberState.PENDING.value
MEMBER = MemberRole.MEMBER.value


class UpsertMemberTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.conversation = create_conversation(created_by=str(self.user.id))

    def test_creates_member(self):
        member, created = ConversationMemberRepository.upsert_member(
            conversation_id=self.conversation.id,
            user_id=self.user.id,
            state=PENDING,
            role=MEMBER,
            invited_by=str(self.user.id),
            now=NOW,
        )

        self.assertTrue(created)
        self.assertEqual(member.state, PENDING)
        self.assertEqual(member.joined_at, NOW)

    def test_reactivates_declined_membership(self):
        create_member(self.conversation, self.user, state=PENDING, is_deleted=True)

        member, created = ConversationMemberRepository.upsert_member(
            conversation_id=self.conversation.id,
            user_id=self.user.id,
            state=PENDING,
            role=MEMBER,
            invited_by=str(self.user.id),
        )

        self.assertFalse(created)
        self.assertFalse(member.is_deleted)
        self.assertEqual(ConversationMemberModel.objects.count(), 1)


class MemberStateTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.conversation = create_conversation(created_by=str(self.user.id))

    def test_get_active_member_ignores_declined(self):
        create_member(self.conversation, self.user, state=PENDING, is_deleted=True)

        self.assertIsNone(
            ConversationMemberRepository.get_active_member(
                self.conversation.id, self.user.id
            )
        )

    def test_set_state_promotes_pending_to_accepted(self):
        create_member(self.conversation, self.user, state=PENDING)

        member = ConversationMemberRepository.set_state(
            self.conversation.id, self.user.id, ACCEPTED
        )

        self.assertIsNotNone(member)
        self.assertEqual(member.state, ACCEPTED)

    def test_set_state_returns_none_when_absent(self):
        self.assertIsNone(
            ConversationMemberRepository.set_state(
                self.conversation.id, self.user.id, ACCEPTED
            )
        )

    def test_soft_delete_marks_membership(self):
        create_member(self.conversation, self.user, state=PENDING)

        member = ConversationMemberRepository.soft_delete(
            self.conversation.id, self.user.id
        )

        self.assertTrue(member.is_deleted)
        self.assertIsNone(
            ConversationMemberRepository.get_active_member(
                self.conversation.id, self.user.id
            )
        )

    def test_list_active_excludes_deleted(self):
        other = create_user()
        create_member(self.conversation, self.user, state=ACCEPTED)
        create_member(self.conversation, other, state=PENDING, is_deleted=True)

        active = ConversationMemberRepository.list_active(self.conversation.id)

        self.assertEqual([m.user_id for m in active], [self.user.id])


class UnreadTests(TestCase):
    def setUp(self):
        self.sender = create_user()
        self.recipient = create_user()
        self.conversation = create_conversation(created_by=str(self.sender.id))
        self.sender_member = create_member(
            self.conversation, self.sender, state=ACCEPTED
        )
        self.recipient_member = create_member(
            self.conversation, self.recipient, state=ACCEPTED
        )

    def _unread(self, member) -> int:
        member.refresh_from_db()
        return member.unread_count

    def test_increment_bumps_everyone_except_sender(self):
        ConversationMemberRepository.increment_unread(
            self.conversation.id, exclude_user_id=self.sender.id
        )

        self.assertEqual(self._unread(self.recipient_member), 1)
        self.assertEqual(self._unread(self.sender_member), 0)

    def test_reset_clears_only_the_caller(self):
        ConversationMemberRepository.increment_unread(
            self.conversation.id, exclude_user_id=self.sender.id
        )

        ConversationMemberRepository.reset_unread(
            self.conversation.id, self.recipient.id
        )

        self.assertEqual(self._unread(self.recipient_member), 0)

    def test_count_unread_conversations_counts_distinct_conversations(self):
        # Two people message the recipient across two conversations.
        other_sender = create_user()
        second = create_conversation(created_by=str(other_sender.id))
        create_member(second, other_sender, state=ACCEPTED)
        create_member(second, self.recipient, state=PENDING)

        ConversationMemberRepository.increment_unread(
            self.conversation.id, exclude_user_id=self.sender.id
        )
        # Two messages in the same conversation still count as one person.
        ConversationMemberRepository.increment_unread(
            self.conversation.id, exclude_user_id=self.sender.id
        )
        ConversationMemberRepository.increment_unread(
            second.id, exclude_user_id=other_sender.id
        )

        self.assertEqual(
            ConversationMemberRepository.count_unread_conversations(self.recipient.id),
            2,
        )

    def test_count_ignores_read_and_own_sends(self):
        self.assertEqual(
            ConversationMemberRepository.count_unread_conversations(self.sender.id),
            0,
        )
