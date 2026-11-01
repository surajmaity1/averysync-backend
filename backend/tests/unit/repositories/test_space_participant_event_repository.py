from datetime import timedelta

from django.test import TestCase

from backend.constants.messages import RepositoryError
from backend.models.space_participant_event import SpaceParticipantEventModel
from backend.repositories.space_participant_event_repository import (
    SpaceParticipantEventRepository,
)
from backend.tests.factories import NOW, create_space, create_user

JOIN = SpaceParticipantEventModel.ParticipantAction.JOIN
MUTE = SpaceParticipantEventModel.ParticipantAction.MUTE


class SpaceParticipantEventRepositoryTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.listener_user = create_user()

    def test_create_persists_join_event(self):
        event = SpaceParticipantEventRepository.create(
            post_id=str(self.space.id),
            target_user_id=str(self.listener_user.id),
            actor=str(self.listener_user.id),
            action=JOIN,
        )

        persisted = SpaceParticipantEventModel.objects.get(id=event.id)
        self.assertEqual(persisted.post_id, self.space.id)
        self.assertEqual(persisted.target_user_id, self.listener_user.id)
        self.assertEqual(persisted.actor, str(self.listener_user.id))
        self.assertEqual(persisted.action, JOIN)
        self.assertIsNone(persisted.reason)
        self.assertIsNone(persisted.muted_until)
        self.assertIsNotNone(persisted.created_at)

    def test_create_persists_mute_event_with_reason_and_horizon(self):
        muted_until = NOW + timedelta(seconds=600)

        event = SpaceParticipantEventRepository.create(
            post_id=str(self.space.id),
            target_user_id=str(self.listener_user.id),
            actor=str(self.host_user.id),
            action=MUTE,
            reason="background noise",
            muted_until=muted_until,
        )

        persisted = SpaceParticipantEventModel.objects.get(id=event.id)
        self.assertEqual(persisted.actor, str(self.host_user.id))
        self.assertEqual(persisted.action, MUTE)
        self.assertEqual(persisted.reason, "background noise")
        self.assertEqual(persisted.muted_until, muted_until)

    def test_create_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantEventRepository.create(
                post_id="not-a-uuid",
                target_user_id=str(self.listener_user.id),
                actor=str(self.listener_user.id),
                action=JOIN,
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_EVENT_CREATE_FAILED.format("").rstrip(": "),
            str(context.exception),
        )

    def test_list_by_post_returns_events_newest_first(self):
        first = SpaceParticipantEventRepository.create(
            post_id=str(self.space.id),
            target_user_id=str(self.listener_user.id),
            actor=str(self.listener_user.id),
            action=JOIN,
        )
        SpaceParticipantEventModel.objects.filter(id=first.id).update(
            created_at=NOW - timedelta(minutes=5)
        )
        second = SpaceParticipantEventRepository.create(
            post_id=str(self.space.id),
            target_user_id=str(self.listener_user.id),
            actor=str(self.host_user.id),
            action=MUTE,
        )

        events = SpaceParticipantEventRepository.list_by_post(
            post_id=str(self.space.id)
        )

        self.assertEqual([event.id for event in events], [second.id, first.id])

    def test_list_by_post_returns_empty_for_space_without_events(self):
        events = SpaceParticipantEventRepository.list_by_post(
            post_id=str(self.space.id)
        )

        self.assertEqual(list(events), [])

    def test_list_by_post_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantEventRepository.list_by_post(post_id="not-a-uuid")

        self.assertIn(
            RepositoryError.PARTICIPANT_FETCH_FAILED.format("").rstrip(": "),
            str(context.exception),
        )
