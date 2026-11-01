import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import (
    CannotFollowSelfException,
    FollowerNotFoundException,
    FollowForbiddenException,
    FollowRequestNotFoundException,
    NotFollowingException,
    UserBlockedException,
)
from backend.models.follow import UserFollowModel
from backend.services.follow_service import FollowService

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
PENDING = UserFollowModel.FollowStatus.PENDING
ACCEPTED = UserFollowModel.FollowStatus.ACCEPTED

SP = "backend.services.follow_service"


def _user(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test User",
        "image": None,
        "is_private": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _edge(follower_id, followee_id, status=ACCEPTED, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "follower_id": follower_id,
        "followee_id": followee_id,
        "status": int(status),
        "requested_at": NOW,
        "responded_at": NOW if status == ACCEPTED else None,
        "created_at": NOW,
        "is_deleted": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FollowServiceTestBase(SimpleTestCase):
    def setUp(self):
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

        patchers = {
            "get_by_id": patch(f"{SP}.UserRepository.get_by_id"),
            "create_or_reactivate": patch(
                f"{SP}.FollowRepository.create_or_reactivate"
            ),
            "soft_delete": patch(f"{SP}.FollowRepository.soft_delete"),
            "accept": patch(f"{SP}.FollowRepository.accept"),
            "exists_accepted": patch(f"{SP}.FollowRepository.exists_accepted"),
            "get_edge": patch(f"{SP}.FollowRepository.get_edge"),
            "list_followers": patch(f"{SP}.FollowRepository.list_followers"),
            "list_following": patch(f"{SP}.FollowRepository.list_following"),
            "list_pending": patch(f"{SP}.FollowRepository.list_pending"),
            "is_blocked": patch(f"{SP}.BlockRepository.is_blocked"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

        self.mocks["is_blocked"].return_value = False
        self.mocks["exists_accepted"].return_value = False


class FollowServiceFollowTests(FollowServiceTestBase):
    def test_follow_public_target_creates_accepted_edge(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=False
        )
        edge = _edge(uuid.UUID(self.caller_id), uuid.UUID(self.target_id), ACCEPTED)
        self.mocks["create_or_reactivate"].return_value = (edge, True)

        dto, created = FollowService.follow(
            follower_id=self.caller_id, target_user_id=self.target_id, now=NOW
        )

        self.assertTrue(created)
        self.assertEqual(dto.status, "ACCEPTED")
        self.mocks["create_or_reactivate"].assert_called_once_with(
            follower_id=self.caller_id,
            followee_id=self.target_id,
            target_status=ACCEPTED,
            requested_at=NOW,
            responded_at=NOW,
        )

    def test_follow_private_target_creates_pending_edge(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=True
        )
        edge = _edge(uuid.UUID(self.caller_id), uuid.UUID(self.target_id), PENDING)
        self.mocks["create_or_reactivate"].return_value = (edge, True)

        dto, created = FollowService.follow(
            follower_id=self.caller_id, target_user_id=self.target_id, now=NOW
        )

        self.assertEqual(dto.status, "PENDING")
        self.mocks["create_or_reactivate"].assert_called_once_with(
            follower_id=self.caller_id,
            followee_id=self.target_id,
            target_status=PENDING,
            requested_at=NOW,
            responded_at=None,
        )

    def test_follow_self_raises_and_touches_no_repo(self):
        with self.assertRaises(CannotFollowSelfException):
            FollowService.follow(
                follower_id=self.caller_id, target_user_id=self.caller_id, now=NOW
            )

        self.mocks["create_or_reactivate"].assert_not_called()

    def test_follow_blocked_raises_user_blocked(self):
        self.mocks["get_by_id"].return_value = _user(id=uuid.UUID(self.target_id))
        self.mocks["is_blocked"].return_value = True

        with self.assertRaises(UserBlockedException):
            FollowService.follow(
                follower_id=self.caller_id, target_user_id=self.target_id, now=NOW
            )

        self.mocks["create_or_reactivate"].assert_not_called()

    def test_follow_missing_target_raises_user_not_found(self):
        self.mocks["get_by_id"].side_effect = UserNotFoundException()

        with self.assertRaises(UserNotFoundException):
            FollowService.follow(
                follower_id=self.caller_id, target_user_id=self.target_id, now=NOW
            )


class FollowServiceUnfollowTests(FollowServiceTestBase):
    def test_unfollow_soft_deletes_edge(self):
        self.mocks["soft_delete"].return_value = _edge(
            uuid.UUID(self.caller_id), uuid.UUID(self.target_id), ACCEPTED
        )

        result = FollowService.unfollow_or_cancel(
            follower_id=self.caller_id, target_user_id=self.target_id
        )

        self.assertIsNone(result)
        self.mocks["soft_delete"].assert_called_once_with(
            follower_id=self.caller_id, followee_id=self.target_id
        )

    def test_unfollow_no_edge_raises_not_following(self):
        self.mocks["soft_delete"].return_value = None

        with self.assertRaises(NotFollowingException):
            FollowService.unfollow_or_cancel(
                follower_id=self.caller_id, target_user_id=self.target_id
            )


class FollowServiceAcceptRejectTests(FollowServiceTestBase):
    def test_accept_returns_accepted_dto(self):
        edge = _edge(uuid.UUID(self.target_id), uuid.UUID(self.caller_id), ACCEPTED)
        self.mocks["accept"].return_value = edge

        dto = FollowService.accept(
            followee_id=self.caller_id, follower_id=self.target_id, now=NOW
        )

        self.assertEqual(dto.status, "ACCEPTED")
        self.mocks["accept"].assert_called_once_with(
            follower_id=self.target_id, followee_id=self.caller_id, responded_at=NOW
        )

    def test_accept_no_pending_raises(self):
        self.mocks["accept"].return_value = None

        with self.assertRaises(FollowRequestNotFoundException):
            FollowService.accept(
                followee_id=self.caller_id, follower_id=self.target_id, now=NOW
            )

    def test_reject_soft_deletes_pending(self):
        self.mocks["soft_delete"].return_value = _edge(
            uuid.UUID(self.target_id), uuid.UUID(self.caller_id), PENDING
        )

        result = FollowService.reject(
            followee_id=self.caller_id, follower_id=self.target_id
        )

        self.assertIsNone(result)
        self.mocks["soft_delete"].assert_called_once_with(
            follower_id=self.target_id,
            followee_id=self.caller_id,
            expected_status=PENDING,
        )

    def test_reject_no_pending_raises(self):
        self.mocks["soft_delete"].return_value = None

        with self.assertRaises(FollowRequestNotFoundException):
            FollowService.reject(followee_id=self.caller_id, follower_id=self.target_id)


class FollowServiceRemoveFollowerTests(FollowServiceTestBase):
    def test_remove_follower_soft_deletes_accepted(self):
        self.mocks["soft_delete"].return_value = _edge(
            uuid.UUID(self.target_id), uuid.UUID(self.caller_id), ACCEPTED
        )

        result = FollowService.remove_follower(
            followee_id=self.caller_id, follower_id=self.target_id
        )

        self.assertIsNone(result)
        self.mocks["soft_delete"].assert_called_once_with(
            follower_id=self.target_id,
            followee_id=self.caller_id,
            expected_status=ACCEPTED,
        )

    def test_remove_follower_none_raises(self):
        self.mocks["soft_delete"].return_value = None

        with self.assertRaises(FollowerNotFoundException):
            FollowService.remove_follower(
                followee_id=self.caller_id, follower_id=self.target_id
            )


class FollowServiceListTests(FollowServiceTestBase):
    def test_get_followers_public_returns_items(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=False
        )
        follower = _user(name="Ada")
        edge = _edge(follower.id, uuid.UUID(self.target_id), ACCEPTED)
        edge.follower = follower
        self.mocks["list_followers"].return_value = ([edge], 1)

        response = FollowService.get_followers(
            viewer_id=self.caller_id,
            target_user_id=self.target_id,
            limit=20,
            offset=0,
        )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.data[0].name, "Ada")

    def test_get_followers_private_non_follower_forbidden(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=True
        )
        self.mocks["exists_accepted"].return_value = False

        with self.assertRaises(FollowForbiddenException):
            FollowService.get_followers(
                viewer_id=self.caller_id,
                target_user_id=self.target_id,
                limit=20,
                offset=0,
            )

    def test_get_followers_private_owner_allowed(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=True
        )
        self.mocks["list_followers"].return_value = ([], 0)

        response = FollowService.get_followers(
            viewer_id=self.target_id,
            target_user_id=self.target_id,
            limit=20,
            offset=0,
        )

        self.assertEqual(response.total, 0)

    def test_get_followers_private_accepted_follower_allowed(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=True
        )
        self.mocks["exists_accepted"].return_value = True
        self.mocks["list_followers"].return_value = ([], 0)

        response = FollowService.get_followers(
            viewer_id=self.caller_id,
            target_user_id=self.target_id,
            limit=20,
            offset=0,
        )

        self.assertEqual(response.total, 0)

    def test_get_followers_blocked_viewer_raises(self):
        self.mocks["is_blocked"].return_value = True

        with self.assertRaises(UserBlockedException):
            FollowService.get_followers(
                viewer_id=self.caller_id,
                target_user_id=self.target_id,
                limit=20,
                offset=0,
            )

    def test_get_following_public_returns_items(self):
        self.mocks["get_by_id"].return_value = _user(
            id=uuid.UUID(self.target_id), is_private=False
        )
        followee = _user(name="Cara")
        edge = _edge(uuid.UUID(self.target_id), followee.id, ACCEPTED)
        edge.followee = followee
        self.mocks["list_following"].return_value = ([edge], 1)

        response = FollowService.get_following(
            viewer_id=self.caller_id,
            target_user_id=self.target_id,
            limit=20,
            offset=0,
        )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.data[0].name, "Cara")

    def test_get_requests_returns_pending(self):
        follower = _user(name="Bob")
        edge = _edge(follower.id, uuid.UUID(self.caller_id), PENDING)
        edge.follower = follower
        self.mocks["list_pending"].return_value = ([edge], 1)

        response = FollowService.get_requests(
            user_id=self.caller_id, limit=20, offset=0
        )

        self.assertEqual(response.total, 1)
        self.assertEqual(response.data[0].name, "Bob")


class FollowServiceRelationshipTests(FollowServiceTestBase):
    def test_relationship_self(self):
        relationship = FollowService.relationship_for(
            viewer_id=self.caller_id, target_id=self.caller_id
        )

        self.assertEqual(relationship.status, "SELF")
        self.assertFalse(relationship.followsYou)

    def test_relationship_following_and_follows_you(self):
        self.mocks["get_edge"].return_value = _edge(
            uuid.UUID(self.caller_id), uuid.UUID(self.target_id), ACCEPTED
        )
        self.mocks["exists_accepted"].return_value = True

        relationship = FollowService.relationship_for(
            viewer_id=self.caller_id, target_id=self.target_id
        )

        self.assertEqual(relationship.status, "FOLLOWING")
        self.assertTrue(relationship.followsYou)

    def test_relationship_pending(self):
        self.mocks["get_edge"].return_value = _edge(
            uuid.UUID(self.caller_id), uuid.UUID(self.target_id), PENDING
        )

        relationship = FollowService.relationship_for(
            viewer_id=self.caller_id, target_id=self.target_id
        )

        self.assertEqual(relationship.status, "PENDING")

    def test_relationship_none_when_no_edge(self):
        self.mocks["get_edge"].return_value = None

        relationship = FollowService.relationship_for(
            viewer_id=self.caller_id, target_id=self.target_id
        )

        self.assertEqual(relationship.status, "NONE")
