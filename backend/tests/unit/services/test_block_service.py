import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import CannotBlockSelfException
from backend.services.block_service import BlockService

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
SP = "backend.services.block_service"


def _block(blocker_id, blocked_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        blocker_id=blocker_id,
        blocked_id=blocked_id,
        created_at=NOW,
    )


class BlockServiceTestBase(TestCase):
    def setUp(self):
        self.blocker_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

        patchers = {
            "get_by_id": patch(f"{SP}.UserRepository.get_by_id"),
            "follow_soft_delete": patch(f"{SP}.FollowRepository.soft_delete"),
            "create_block": patch(f"{SP}.BlockRepository.create_or_reactivate"),
            "block_soft_delete": patch(f"{SP}.BlockRepository.soft_delete"),
            "list_blocks": patch(f"{SP}.BlockRepository.list_blocks"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)


class BlockServiceBlockTests(BlockServiceTestBase):
    def test_block_severs_both_edges_and_upserts_block(self):
        self.mocks["get_by_id"].return_value = SimpleNamespace(
            id=uuid.UUID(self.target_id)
        )
        self.mocks["follow_soft_delete"].return_value = None
        block = _block(uuid.UUID(self.blocker_id), uuid.UUID(self.target_id))
        self.mocks["create_block"].return_value = (block, True)

        dto, created = BlockService.block(
            blocker_id=self.blocker_id, target_user_id=self.target_id
        )

        self.assertTrue(created)
        self.assertEqual(str(dto.blockedId), self.target_id)
        self.assertEqual(self.mocks["follow_soft_delete"].call_count, 2)
        self.mocks["follow_soft_delete"].assert_any_call(
            follower_id=self.blocker_id, followee_id=self.target_id
        )
        self.mocks["follow_soft_delete"].assert_any_call(
            follower_id=self.target_id, followee_id=self.blocker_id
        )
        self.mocks["create_block"].assert_called_once_with(
            blocker_id=self.blocker_id, blocked_id=self.target_id
        )

    def test_block_self_raises(self):
        with self.assertRaises(CannotBlockSelfException):
            BlockService.block(
                blocker_id=self.blocker_id, target_user_id=self.blocker_id
            )

        self.mocks["create_block"].assert_not_called()

    def test_block_missing_target_raises_user_not_found(self):
        self.mocks["get_by_id"].side_effect = UserNotFoundException()

        with self.assertRaises(UserNotFoundException):
            BlockService.block(
                blocker_id=self.blocker_id, target_user_id=self.target_id
            )

        self.mocks["create_block"].assert_not_called()


class BlockServiceUnblockTests(BlockServiceTestBase):
    def test_unblock_soft_deletes(self):
        self.mocks["block_soft_delete"].return_value = _block(
            uuid.UUID(self.blocker_id), uuid.UUID(self.target_id)
        )

        result = BlockService.unblock(
            blocker_id=self.blocker_id, target_user_id=self.target_id
        )

        self.assertIsNone(result)
        self.mocks["block_soft_delete"].assert_called_once_with(
            blocker_id=self.blocker_id, blocked_id=self.target_id
        )

    def test_unblock_is_idempotent_when_no_block(self):
        self.mocks["block_soft_delete"].return_value = None

        result = BlockService.unblock(
            blocker_id=self.blocker_id, target_user_id=self.target_id
        )

        self.assertIsNone(result)


class BlockServiceListTests(BlockServiceTestBase):
    def test_get_blocks_returns_items(self):
        blocked = SimpleNamespace(id=uuid.uuid4(), name="Zed", image=None)
        row = SimpleNamespace(
            id=uuid.uuid4(),
            blocked_id=blocked.id,
            blocked=blocked,
            created_at=NOW,
        )
        self.mocks["list_blocks"].return_value = ([row], 1)

        response = BlockService.get_blocks(user_id=self.blocker_id, limit=20, offset=0)

        self.assertEqual(response.total, 1)
        self.assertEqual(response.data[0].name, "Zed")
