from django.test import TestCase

from backend.constants.messages import RepositoryError
from backend.models.follow import UserFollowModel
from backend.repositories.follow_repository import FollowRepository
from backend.tests.factories import NOW, create_follow, create_user

PENDING = UserFollowModel.FollowStatus.PENDING
ACCEPTED = UserFollowModel.FollowStatus.ACCEPTED


def _counts(user):
    user.refresh_from_db()
    return user.follower_count, user.following_count


class FollowRepositoryCreateOrReactivateTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_creates_accepted_edge_and_increments_counts(self):
        edge, created = FollowRepository.create_or_reactivate(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            target_status=ACCEPTED,
            requested_at=NOW,
            responded_at=NOW,
        )

        self.assertTrue(created)
        persisted = UserFollowModel.objects.get(id=edge.id)
        self.assertEqual(persisted.status, ACCEPTED)
        self.assertEqual(persisted.responded_at, NOW)
        self.assertFalse(persisted.is_deleted)
        self.assertEqual(persisted.created_by, str(self.follower.id))
        self.assertEqual(_counts(self.followee), (1, 0))
        self.assertEqual(_counts(self.follower), (0, 1))

    def test_creates_pending_edge_without_count_change(self):
        edge, created = FollowRepository.create_or_reactivate(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            target_status=PENDING,
            requested_at=NOW,
            responded_at=None,
        )

        self.assertTrue(created)
        self.assertEqual(edge.status, PENDING)
        self.assertIsNone(edge.responded_at)
        self.assertEqual(_counts(self.followee), (0, 0))
        self.assertEqual(_counts(self.follower), (0, 0))

    def test_reactivates_soft_deleted_edge_to_accepted(self):
        existing = create_follow(
            self.follower,
            self.followee,
            status=PENDING,
            responded_at=None,
            is_deleted=True,
        )

        edge, created = FollowRepository.create_or_reactivate(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            target_status=ACCEPTED,
            requested_at=NOW,
            responded_at=NOW,
        )

        self.assertFalse(created)
        self.assertEqual(edge.id, existing.id)
        self.assertFalse(edge.is_deleted)
        self.assertEqual(edge.status, ACCEPTED)
        self.assertEqual(_counts(self.followee), (1, 0))
        self.assertEqual(
            UserFollowModel.objects.filter(
                follower=self.follower, followee=self.followee
            ).count(),
            1,
        )

    def test_idempotent_reaccept_does_not_double_count(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)
        self.followee.follower_count = 1
        self.followee.save()
        self.follower.following_count = 1
        self.follower.save()

        _, created = FollowRepository.create_or_reactivate(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            target_status=ACCEPTED,
            requested_at=NOW,
            responded_at=NOW,
        )

        self.assertFalse(created)
        self.assertEqual(_counts(self.followee), (1, 0))
        self.assertEqual(_counts(self.follower), (0, 1))

    def test_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.create_or_reactivate(
                follower_id="not-a-uuid",
                followee_id=str(self.followee.id),
                target_status=ACCEPTED,
                requested_at=NOW,
                responded_at=NOW,
            )

        self.assertIn(
            RepositoryError.FOLLOW_UPSERT_FAILED.format(""), str(ctx.exception)
        )

    def test_self_edge_violates_check_constraint(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.create_or_reactivate(
                follower_id=str(self.follower.id),
                followee_id=str(self.follower.id),
                target_status=ACCEPTED,
                requested_at=NOW,
                responded_at=NOW,
            )

        self.assertIn(
            RepositoryError.FOLLOW_UPSERT_FAILED.format(""), str(ctx.exception)
        )


class FollowRepositoryGetEdgeTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_get_edge_returns_existing_row(self):
        created = create_follow(self.follower, self.followee, status=ACCEPTED)

        edge = FollowRepository.get_edge(
            follower_id=str(self.follower.id), followee_id=str(self.followee.id)
        )

        self.assertEqual(edge.id, created.id)

    def test_get_edge_returns_none_when_missing(self):
        edge = FollowRepository.get_edge(
            follower_id=str(self.follower.id), followee_id=str(self.followee.id)
        )

        self.assertIsNone(edge)

    def test_get_edge_for_update_returns_row(self):
        created = create_follow(self.follower, self.followee, status=ACCEPTED)

        edge = FollowRepository.get_edge(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            for_update=True,
        )

        self.assertEqual(edge.id, created.id)

    def test_get_edge_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.get_edge(
                follower_id="not-a-uuid", followee_id=str(self.followee.id)
            )

        self.assertIn(
            RepositoryError.FOLLOW_FETCH_FAILED.format(""), str(ctx.exception)
        )


class FollowRepositoryDowngradeTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_reactivate_from_accepted_to_pending_decrements_counts(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)
        self.followee.follower_count = 1
        self.followee.save()
        self.follower.following_count = 1
        self.follower.save()

        edge, created = FollowRepository.create_or_reactivate(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            target_status=PENDING,
            requested_at=NOW,
            responded_at=None,
        )

        self.assertFalse(created)
        self.assertEqual(edge.status, PENDING)
        self.assertEqual(_counts(self.followee), (0, 0))
        self.assertEqual(_counts(self.follower), (0, 0))


class FollowRepositoryErrorPathTests(TestCase):
    def setUp(self):
        self.followee = create_user()

    def test_accept_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.accept(
                follower_id="not-a-uuid",
                followee_id=str(self.followee.id),
                responded_at=NOW,
            )

        self.assertIn(
            RepositoryError.FOLLOW_UPSERT_FAILED.format(""), str(ctx.exception)
        )

    def test_soft_delete_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.soft_delete(
                follower_id="not-a-uuid", followee_id=str(self.followee.id)
            )

        self.assertIn(
            RepositoryError.FOLLOW_UPSERT_FAILED.format(""), str(ctx.exception)
        )

    def test_exists_accepted_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.exists_accepted(
                follower_id="not-a-uuid", followee_id=str(self.followee.id)
            )

        self.assertIn(
            RepositoryError.FOLLOW_FETCH_FAILED.format(""), str(ctx.exception)
        )


class FollowRepositoryAcceptTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_accept_pending_sets_accepted_and_increments_counts(self):
        create_follow(self.follower, self.followee, status=PENDING, responded_at=None)

        edge = FollowRepository.accept(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            responded_at=NOW,
        )

        self.assertIsNotNone(edge)
        self.assertEqual(edge.status, ACCEPTED)
        self.assertEqual(edge.responded_at, NOW)
        self.assertEqual(_counts(self.followee), (1, 0))
        self.assertEqual(_counts(self.follower), (0, 1))

    def test_accept_idempotent_when_already_accepted(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)
        self.followee.follower_count = 1
        self.followee.save()

        edge = FollowRepository.accept(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            responded_at=NOW,
        )

        self.assertEqual(edge.status, ACCEPTED)
        self.assertEqual(_counts(self.followee), (1, 0))

    def test_accept_returns_none_when_no_pending_request(self):
        edge = FollowRepository.accept(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            responded_at=NOW,
        )

        self.assertIsNone(edge)


class FollowRepositorySoftDeleteTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_soft_delete_accepted_decrements_counts(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)
        self.followee.follower_count = 1
        self.followee.save()
        self.follower.following_count = 1
        self.follower.save()

        edge = FollowRepository.soft_delete(
            follower_id=str(self.follower.id), followee_id=str(self.followee.id)
        )

        self.assertIsNotNone(edge)
        self.assertTrue(UserFollowModel.objects.get(id=edge.id).is_deleted)
        self.assertEqual(_counts(self.followee), (0, 0))
        self.assertEqual(_counts(self.follower), (0, 0))

    def test_soft_delete_pending_does_not_change_counts(self):
        create_follow(self.follower, self.followee, status=PENDING, responded_at=None)

        edge = FollowRepository.soft_delete(
            follower_id=str(self.follower.id), followee_id=str(self.followee.id)
        )

        self.assertTrue(edge.is_deleted)
        self.assertEqual(_counts(self.followee), (0, 0))

    def test_soft_delete_returns_none_when_no_active_edge(self):
        edge = FollowRepository.soft_delete(
            follower_id=str(self.follower.id), followee_id=str(self.followee.id)
        )

        self.assertIsNone(edge)

    def test_soft_delete_with_expected_status_ignores_mismatch(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)

        edge = FollowRepository.soft_delete(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            expected_status=PENDING,
        )

        self.assertIsNone(edge)
        self.assertFalse(
            UserFollowModel.objects.get(
                follower=self.follower, followee=self.followee
            ).is_deleted
        )

    def test_soft_delete_with_expected_status_accepted_matches(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)
        self.followee.follower_count = 1
        self.followee.save()

        edge = FollowRepository.soft_delete(
            follower_id=str(self.follower.id),
            followee_id=str(self.followee.id),
            expected_status=ACCEPTED,
        )

        self.assertIsNotNone(edge)
        self.assertEqual(_counts(self.followee), (0, 0))


class FollowRepositoryExistsAcceptedTests(TestCase):
    def setUp(self):
        self.follower = create_user()
        self.followee = create_user()

    def test_true_for_accepted_active_edge(self):
        create_follow(self.follower, self.followee, status=ACCEPTED)

        self.assertTrue(
            FollowRepository.exists_accepted(
                follower_id=str(self.follower.id),
                followee_id=str(self.followee.id),
            )
        )

    def test_false_for_pending_edge(self):
        create_follow(self.follower, self.followee, status=PENDING, responded_at=None)

        self.assertFalse(
            FollowRepository.exists_accepted(
                follower_id=str(self.follower.id),
                followee_id=str(self.followee.id),
            )
        )

    def test_false_for_soft_deleted_edge(self):
        create_follow(self.follower, self.followee, status=ACCEPTED, is_deleted=True)

        self.assertFalse(
            FollowRepository.exists_accepted(
                follower_id=str(self.follower.id),
                followee_id=str(self.followee.id),
            )
        )

    def test_false_when_missing(self):
        self.assertFalse(
            FollowRepository.exists_accepted(
                follower_id=str(self.follower.id),
                followee_id=str(self.followee.id),
            )
        )


class FollowRepositoryListTests(TestCase):
    def setUp(self):
        self.owner = create_user()

    def test_list_followers_returns_accepted_only_with_total(self):
        f1 = create_user()
        f2 = create_user()
        pending = create_user()
        create_follow(f1, self.owner, status=ACCEPTED)
        create_follow(f2, self.owner, status=ACCEPTED)
        create_follow(pending, self.owner, status=PENDING, responded_at=None)

        edges, total = FollowRepository.list_followers(
            user_id=str(self.owner.id), limit=20, offset=0
        )

        self.assertEqual(total, 2)
        self.assertEqual(len(edges), 2)
        follower_ids = {e.follower_id for e in edges}
        self.assertEqual(follower_ids, {f1.id, f2.id})

    def test_list_following_returns_accepted_only(self):
        t1 = create_user()
        create_follow(self.owner, t1, status=ACCEPTED)

        edges, total = FollowRepository.list_following(
            user_id=str(self.owner.id), limit=20, offset=0
        )

        self.assertEqual(total, 1)
        self.assertEqual(edges[0].followee_id, t1.id)

    def test_list_pending_returns_pending_inbox(self):
        req = create_user()
        create_follow(req, self.owner, status=PENDING, responded_at=None)
        create_follow(create_user(), self.owner, status=ACCEPTED)

        edges, total = FollowRepository.list_pending(
            user_id=str(self.owner.id), limit=20, offset=0
        )

        self.assertEqual(total, 1)
        self.assertEqual(edges[0].follower_id, req.id)

    def test_list_followers_respects_limit_and_offset(self):
        for _ in range(3):
            create_follow(create_user(), self.owner, status=ACCEPTED)

        page, total = FollowRepository.list_followers(
            user_id=str(self.owner.id), limit=2, offset=0
        )
        page_two, _ = FollowRepository.list_followers(
            user_id=str(self.owner.id), limit=2, offset=2
        )

        self.assertEqual(total, 3)
        self.assertEqual(len(page), 2)
        self.assertEqual(len(page_two), 1)

    def test_list_followers_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            FollowRepository.list_followers(user_id="not-a-uuid", limit=20, offset=0)

        self.assertIn(RepositoryError.FOLLOW_LIST_FAILED.format(""), str(ctx.exception))
