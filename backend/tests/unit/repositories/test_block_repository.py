from django.test import TestCase

from backend.constants.messages import RepositoryError
from backend.models.block import UserBlockModel
from backend.repositories.block_repository import BlockRepository
from backend.tests.factories import create_block, create_user


class BlockRepositoryCreateOrReactivateTests(TestCase):
    def setUp(self):
        self.blocker = create_user()
        self.blocked = create_user()

    def test_creates_block_row(self):
        block, created = BlockRepository.create_or_reactivate(
            blocker_id=str(self.blocker.id), blocked_id=str(self.blocked.id)
        )

        self.assertTrue(created)
        persisted = UserBlockModel.objects.get(id=block.id)
        self.assertFalse(persisted.is_deleted)
        self.assertEqual(persisted.created_by, str(self.blocker.id))

    def test_reactivates_soft_deleted_block(self):
        existing = create_block(self.blocker, self.blocked, is_deleted=True)

        block, created = BlockRepository.create_or_reactivate(
            blocker_id=str(self.blocker.id), blocked_id=str(self.blocked.id)
        )

        self.assertFalse(created)
        self.assertEqual(block.id, existing.id)
        self.assertFalse(block.is_deleted)

    def test_self_block_violates_check_constraint(self):
        with self.assertRaises(ValueError) as ctx:
            BlockRepository.create_or_reactivate(
                blocker_id=str(self.blocker.id), blocked_id=str(self.blocker.id)
            )

        self.assertIn(
            RepositoryError.BLOCK_UPSERT_FAILED.format(""), str(ctx.exception)
        )


class BlockRepositorySoftDeleteTests(TestCase):
    def setUp(self):
        self.blocker = create_user()
        self.blocked = create_user()

    def test_soft_delete_active_block(self):
        create_block(self.blocker, self.blocked)

        block = BlockRepository.soft_delete(
            blocker_id=str(self.blocker.id), blocked_id=str(self.blocked.id)
        )

        self.assertIsNotNone(block)
        self.assertTrue(UserBlockModel.objects.get(id=block.id).is_deleted)

    def test_soft_delete_returns_none_when_no_active_block(self):
        block = BlockRepository.soft_delete(
            blocker_id=str(self.blocker.id), blocked_id=str(self.blocked.id)
        )

        self.assertIsNone(block)

    def test_soft_delete_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            BlockRepository.soft_delete(
                blocker_id="not-a-uuid", blocked_id=str(self.blocked.id)
            )

        self.assertIn(
            RepositoryError.BLOCK_UPSERT_FAILED.format(""), str(ctx.exception)
        )


class BlockRepositoryIsBlockedTests(TestCase):
    def setUp(self):
        self.a = create_user()
        self.b = create_user()

    def test_true_when_a_blocked_b(self):
        create_block(self.a, self.b)

        self.assertTrue(BlockRepository.is_blocked(str(self.a.id), str(self.b.id)))

    def test_true_in_reverse_direction(self):
        create_block(self.a, self.b)

        self.assertTrue(BlockRepository.is_blocked(str(self.b.id), str(self.a.id)))

    def test_false_when_no_active_block(self):
        create_block(self.a, self.b, is_deleted=True)

        self.assertFalse(BlockRepository.is_blocked(str(self.a.id), str(self.b.id)))

    def test_is_blocked_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            BlockRepository.is_blocked("not-a-uuid", str(self.b.id))

        self.assertIn(RepositoryError.BLOCK_FETCH_FAILED.format(""), str(ctx.exception))


class BlockRepositoryListTests(TestCase):
    def setUp(self):
        self.blocker = create_user()

    def test_list_blocks_returns_active_with_total(self):
        b1 = create_user()
        b2 = create_user()
        create_block(self.blocker, b1)
        create_block(self.blocker, b2)
        create_block(self.blocker, create_user(), is_deleted=True)

        blocks, total = BlockRepository.list_blocks(
            user_id=str(self.blocker.id), limit=20, offset=0
        )

        self.assertEqual(total, 2)
        self.assertEqual({b.blocked_id for b in blocks}, {b1.id, b2.id})

    def test_list_blocks_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            BlockRepository.list_blocks(user_id="not-a-uuid", limit=20, offset=0)

        self.assertIn(RepositoryError.BLOCK_FETCH_FAILED.format(""), str(ctx.exception))
