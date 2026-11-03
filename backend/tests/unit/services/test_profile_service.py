import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.dto.follow_dto import RelationshipDTO
from backend.dto.profile_dto import UpdateProfileDTO
from backend.exceptions.follow_exception import UserBlockedException
from backend.services.user_service import UserService

SP = "backend.services.user_service"


def _user(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Ada",
        "image": "https://img",
        "is_private": True,
        "follower_count": 12,
        "following_count": 7,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class UserServiceUpdateProfileTests(SimpleTestCase):
    @patch(f"{SP}.UserRepository.update_profile")
    def test_update_profile_returns_profile_dto_with_self_relationship(
        self, mocked_update
    ):
        user = _user(is_private=True)
        mocked_update.return_value = user

        dto = UserService.update_profile(
            user_id=str(user.id), dto=UpdateProfileDTO(isPrivate=True)
        )

        self.assertTrue(dto.isPrivate)
        self.assertEqual(dto.followerCount, 12)
        self.assertEqual(dto.relationship.status, "SELF")
        mocked_update.assert_called_once_with(user_id=str(user.id), is_private=True)


class UserServiceGetProfileTests(SimpleTestCase):
    def setUp(self):
        self.viewer_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

        patchers = {
            "is_blocked": patch(f"{SP}.BlockRepository.is_blocked"),
            "get_by_id": patch(f"{SP}.UserRepository.get_by_id"),
            "relationship_for": patch(f"{SP}.FollowService.relationship_for"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        self.mocks["is_blocked"].return_value = False

    def test_get_profile_returns_dto_with_relationship(self):
        self.mocks["get_by_id"].return_value = _user(id=uuid.UUID(self.target_id))
        self.mocks["relationship_for"].return_value = RelationshipDTO(
            status="FOLLOWING", followsYou=True
        )

        dto = UserService.get_profile(
            viewer_id=self.viewer_id, target_user_id=self.target_id
        )

        self.assertEqual(dto.relationship.status, "FOLLOWING")
        self.assertTrue(dto.relationship.followsYou)
        self.assertEqual(dto.followingCount, 7)

    def test_get_profile_blocked_viewer_raises(self):
        self.mocks["is_blocked"].return_value = True

        with self.assertRaises(UserBlockedException):
            UserService.get_profile(
                viewer_id=self.viewer_id, target_user_id=self.target_id
            )
