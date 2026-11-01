from datetime import timedelta

from django.test import TestCase

from backend.constants.messages import RepositoryError
from backend.models.space_participant import SpaceParticipantModel
from backend.repositories.space_participant_repository import (
    SpaceParticipantRepository,
)
from backend.tests.factories import NOW, create_participant, create_space, create_user

HOST = SpaceParticipantModel.ParticipantRole.HOST
LISTENER = SpaceParticipantModel.ParticipantRole.LISTENER


class SpaceParticipantRepositoryUpsertJoinTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.listener_user = create_user()

    def test_upsert_join_creates_row_on_first_join(self):
        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            role=LISTENER,
            joined_at=NOW,
        )

        self.assertTrue(created)
        persisted = SpaceParticipantModel.objects.get(id=participant.id)
        self.assertEqual(persisted.post_id, self.space.id)
        self.assertEqual(persisted.user_id, self.listener_user.id)
        self.assertEqual(persisted.role, LISTENER)
        self.assertEqual(persisted.first_joined_at, NOW)
        self.assertEqual(persisted.last_joined_at, NOW)
        self.assertIsNone(persisted.left_at)
        self.assertFalse(persisted.is_muted)
        self.assertIsNone(persisted.muted_until)
        self.assertEqual(persisted.created_by, str(self.listener_user.id))
        self.assertIsNotNone(persisted.created_at)

    def test_upsert_join_reactivates_left_row_preserving_mute_and_role(self):
        rejoin_at = NOW + timedelta(minutes=30)
        existing = create_participant(
            self.space,
            self.listener_user,
            left_at=NOW + timedelta(minutes=10),
            is_muted=True,
            muted_until=NOW + timedelta(hours=1),
            muted_by=str(self.host_user.id),
            muted_at=NOW,
        )

        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            role=LISTENER,
            joined_at=rejoin_at,
        )

        self.assertFalse(created)
        self.assertEqual(participant.id, existing.id)
        self.assertIsNone(participant.left_at)
        self.assertEqual(participant.first_joined_at, NOW)
        self.assertEqual(participant.last_joined_at, rejoin_at)
        self.assertTrue(participant.is_muted)
        self.assertEqual(participant.muted_until, NOW + timedelta(hours=1))
        self.assertEqual(participant.muted_by, str(self.host_user.id))
        self.assertEqual(
            SpaceParticipantModel.objects.filter(
                post=self.space, user=self.listener_user
            ).count(),
            1,
        )

    def test_upsert_join_does_not_demote_existing_role_on_rejoin(self):
        create_participant(
            self.space,
            self.host_user,
            role=HOST,
            left_at=NOW + timedelta(minutes=5),
        )

        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=str(self.space.id),
            user_id=str(self.host_user.id),
            role=HOST,
            joined_at=NOW + timedelta(minutes=10),
        )

        self.assertFalse(created)
        self.assertEqual(participant.role, HOST)

    def test_upsert_join_while_active_is_idempotent(self):
        create_participant(self.space, self.listener_user)

        participant, created = SpaceParticipantRepository.upsert_join(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            role=LISTENER,
            joined_at=NOW + timedelta(minutes=1),
        )

        self.assertFalse(created)
        self.assertEqual(participant.last_joined_at, NOW + timedelta(minutes=1))
        self.assertEqual(
            SpaceParticipantModel.objects.filter(
                post=self.space, user=self.listener_user
            ).count(),
            1,
        )

    def test_upsert_join_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.upsert_join(
                post_id="not-a-uuid",
                user_id=str(self.listener_user.id),
                role=LISTENER,
                joined_at=NOW,
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_UPSERT_FAILED.format("").rstrip(": "),
            str(context.exception),
        )


class SpaceParticipantRepositoryGetActiveTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.listener_user = create_user()

    def test_get_active_returns_active_participant(self):
        created = create_participant(self.space, self.listener_user)

        fetched = SpaceParticipantRepository.get_active(
            post_id=str(self.space.id), user_id=str(self.listener_user.id)
        )

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)

    def test_get_active_returns_none_when_never_joined(self):
        fetched = SpaceParticipantRepository.get_active(
            post_id=str(self.space.id), user_id=str(self.listener_user.id)
        )

        self.assertIsNone(fetched)

    def test_get_active_returns_none_when_left(self):
        create_participant(
            self.space, self.listener_user, left_at=NOW + timedelta(minutes=10)
        )

        fetched = SpaceParticipantRepository.get_active(
            post_id=str(self.space.id), user_id=str(self.listener_user.id)
        )

        self.assertIsNone(fetched)

    def test_get_active_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.get_active(
                post_id="not-a-uuid", user_id=str(self.listener_user.id)
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_FETCH_FAILED.format("").rstrip(": "),
            str(context.exception),
        )


class SpaceParticipantRepositoryListTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.active = create_participant(self.space, self.host_user, role=HOST)
        self.departed_user = create_user()
        self.departed = create_participant(
            self.space, self.departed_user, left_at=NOW + timedelta(minutes=10)
        )

    def test_list_by_post_returns_only_active_by_default(self):
        participants = SpaceParticipantRepository.list_by_post(
            post_id=str(self.space.id)
        )

        self.assertEqual([p.id for p in participants], [self.active.id])

    def test_list_by_post_includes_left_rows_when_requested(self):
        participants = SpaceParticipantRepository.list_by_post(
            post_id=str(self.space.id), include_left=True
        )

        self.assertCountEqual(
            [p.id for p in participants], [self.active.id, self.departed.id]
        )

    def test_list_by_post_returns_empty_for_space_without_participants(self):
        other_space = create_space(created_by=str(self.host_user.id))

        participants = SpaceParticipantRepository.list_by_post(
            post_id=str(other_space.id)
        )

        self.assertEqual(list(participants), [])

    def test_list_by_post_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.list_by_post(post_id="not-a-uuid")

        self.assertIn(
            RepositoryError.PARTICIPANT_FETCH_FAILED.format("").rstrip(": "),
            str(context.exception),
        )


class SpaceParticipantRepositoryMuteTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.listener_user = create_user()
        self.participant = create_participant(self.space, self.listener_user)

    def test_set_mute_persists_mute_columns(self):
        muted_until = NOW + timedelta(seconds=600)

        updated = SpaceParticipantRepository.set_mute(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            muted_until=muted_until,
            muted_by=str(self.host_user.id),
            muted_at=NOW,
        )

        self.assertTrue(updated.is_muted)
        self.assertEqual(updated.muted_until, muted_until)
        self.assertEqual(updated.muted_by, str(self.host_user.id))
        self.assertEqual(updated.muted_at, NOW)
        persisted = SpaceParticipantModel.objects.get(id=self.participant.id)
        self.assertTrue(persisted.is_muted)

    def test_set_mute_with_null_horizon_persists_permanent_mute(self):
        updated = SpaceParticipantRepository.set_mute(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            muted_until=None,
            muted_by=str(self.host_user.id),
            muted_at=NOW,
        )

        self.assertTrue(updated.is_muted)
        self.assertIsNone(updated.muted_until)

    def test_set_mute_returns_none_for_left_participant(self):
        self.participant.left_at = NOW + timedelta(minutes=10)
        self.participant.save()

        updated = SpaceParticipantRepository.set_mute(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            muted_until=None,
            muted_by=str(self.host_user.id),
            muted_at=NOW,
        )

        self.assertIsNone(updated)

    def test_clear_mute_resets_all_mute_columns(self):
        self.participant.is_muted = True
        self.participant.muted_until = NOW + timedelta(hours=1)
        self.participant.muted_by = str(self.host_user.id)
        self.participant.muted_at = NOW
        self.participant.save()

        updated = SpaceParticipantRepository.clear_mute(
            post_id=str(self.space.id), user_id=str(self.listener_user.id)
        )

        self.assertFalse(updated.is_muted)
        self.assertIsNone(updated.muted_until)
        self.assertIsNone(updated.muted_by)
        self.assertIsNone(updated.muted_at)

    def test_clear_mute_returns_none_for_never_joined_user(self):
        stranger = create_user()

        updated = SpaceParticipantRepository.clear_mute(
            post_id=str(self.space.id), user_id=str(stranger.id)
        )

        self.assertIsNone(updated)

    def test_update_active_translates_fetch_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.set_mute(
                post_id="not-a-uuid",
                user_id=str(self.listener_user.id),
                muted_until=None,
                muted_by=str(self.host_user.id),
                muted_at=NOW,
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_FETCH_FAILED.format("").rstrip(": "),
            str(context.exception),
        )

    def test_update_active_translates_save_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.set_mute(
                post_id=str(self.space.id),
                user_id=str(self.listener_user.id),
                muted_until=None,
                muted_by="x" * 200,
                muted_at=NOW,
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_UPSERT_FAILED.format("").rstrip(": "),
            str(context.exception),
        )


class SpaceParticipantRepositoryLeaveTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))
        self.listener_user = create_user()

    def test_mark_left_stamps_left_at_and_keeps_mute_columns(self):
        left_at = NOW + timedelta(minutes=45)
        create_participant(
            self.space,
            self.listener_user,
            is_muted=True,
            muted_until=NOW + timedelta(hours=1),
            muted_by=str(self.host_user.id),
            muted_at=NOW,
        )

        updated = SpaceParticipantRepository.mark_left(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            left_at=left_at,
        )

        self.assertEqual(updated.left_at, left_at)
        self.assertTrue(updated.is_muted)
        self.assertEqual(updated.muted_until, NOW + timedelta(hours=1))

    def test_mark_left_returns_none_when_already_left(self):
        create_participant(
            self.space, self.listener_user, left_at=NOW + timedelta(minutes=10)
        )

        updated = SpaceParticipantRepository.mark_left(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            left_at=NOW + timedelta(minutes=20),
        )

        self.assertIsNone(updated)

    def test_mark_left_returns_none_when_never_joined(self):
        updated = SpaceParticipantRepository.mark_left(
            post_id=str(self.space.id),
            user_id=str(self.listener_user.id),
            left_at=NOW,
        )

        self.assertIsNone(updated)


class SpaceParticipantRepositoryCloseOutTests(TestCase):
    def setUp(self):
        self.host_user = create_user()
        self.space = create_space(created_by=str(self.host_user.id))

    def test_close_out_stamps_left_at_on_all_active_participants(self):
        ended_at = NOW + timedelta(hours=1)
        active_users = [create_user() for _ in range(3)]
        for user in active_users:
            create_participant(self.space, user)
        already_left_user = create_user()
        create_participant(
            self.space, already_left_user, left_at=NOW + timedelta(minutes=5)
        )

        updated_count = SpaceParticipantRepository.close_out(
            post_id=str(self.space.id), ended_at=ended_at
        )

        self.assertEqual(updated_count, 3)
        self.assertFalse(
            SpaceParticipantModel.objects.filter(
                post=self.space, left_at__isnull=True
            ).exists()
        )
        untouched = SpaceParticipantModel.objects.get(user=already_left_user)
        self.assertEqual(untouched.left_at, NOW + timedelta(minutes=5))

    def test_close_out_does_not_touch_other_spaces(self):
        other_space = create_space(created_by=str(self.host_user.id))
        create_participant(other_space, self.host_user)

        updated_count = SpaceParticipantRepository.close_out(
            post_id=str(self.space.id), ended_at=NOW + timedelta(hours=1)
        )

        self.assertEqual(updated_count, 0)
        self.assertTrue(
            SpaceParticipantModel.objects.filter(
                post=other_space, left_at__isnull=True
            ).exists()
        )

    def test_close_out_translates_db_error_to_repository_error(self):
        with self.assertRaises(ValueError) as context:
            SpaceParticipantRepository.close_out(
                post_id="not-a-uuid", ended_at=NOW + timedelta(hours=1)
            )

        self.assertIn(
            RepositoryError.PARTICIPANT_UPSERT_FAILED.format("").rstrip(": "),
            str(context.exception),
        )
