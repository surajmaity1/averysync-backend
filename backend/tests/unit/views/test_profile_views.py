import json
import uuid
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import NoReverseMatch, resolve, reverse
from rest_framework import status

from backend.dto.follow_dto import RelationshipDTO
from backend.dto.profile_dto import ProfileDTO
from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import UserBlockedException
from backend.views.user import UserDetailView, UsersView

USER_SERVICE = "backend.views.user.UserService"


def _profile_dto(user_id, relationship_status="SELF", follows_you=False):
    return ProfileDTO(
        id=user_id,
        name="Ada",
        image="https://img",
        isPrivate=True,
        followerCount=10,
        followingCount=5,
        relationship=RelationshipDTO(
            status=relationship_status, followsYou=follows_you
        ),
    )


class UsersViewPatchTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    def _patch(self, body, query="?profile=true"):
        request = self.factory.patch(
            f"/v1/users{query}",
            data=json.dumps(body),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return UsersView.as_view()(request)

    @patch(f"{USER_SERVICE}.update_profile")
    def test_patch_returns_200(self, mocked):
        mocked.return_value = _profile_dto(uuid.UUID(self.caller_id))
        response = self._patch({"isPrivate": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["isPrivate"])

    @patch(f"{USER_SERVICE}.update_profile")
    def test_patch_updates_authenticated_user(self, mocked):
        mocked.return_value = _profile_dto(uuid.UUID(self.caller_id))
        self._patch({"isPrivate": True})

        _, called_kwargs = mocked.call_args
        self.assertEqual(called_kwargs["user_id"], self.caller_id)
        self.assertTrue(called_kwargs["dto"].isPrivate)

    def test_patch_without_profile_true_returns_404(self):
        for query in ["", "?profile=false", "?profile=TRUE", "?profile=1"]:
            with self.subTest(query=query):
                response = self._patch({"isPrivate": True}, query=query)

                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertEqual(response.data["statusCode"], status.HTTP_404_NOT_FOUND)
                self.assertEqual(response.data["message"], "Resource not found")

    @patch(f"{USER_SERVICE}.update_profile")
    def test_patch_without_profile_true_does_not_update(self, mocked):
        self._patch({"isPrivate": True}, query="")

        mocked.assert_not_called()

    def test_patch_missing_is_private_returns_400(self):
        response = self._patch({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_unknown_field_returns_400(self):
        response = self._patch({"isPrivate": True, "isPublic": False})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{USER_SERVICE}.update_profile")
    def test_patch_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._patch({"isPrivate": True})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileRouteTests(SimpleTestCase):
    def test_users_me_route_is_removed(self):
        with self.assertRaises(NoReverseMatch):
            reverse("user_profile_me")

    def test_users_route_resolves_to_users_view(self):
        self.assertIs(resolve("/v1/users").func.view_class, UsersView)


class UserDetailProfileGetTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _get(self, user_id):
        request = self.factory.get("/v1/users/x")
        request.user_id = self.caller_id
        return UserDetailView.as_view()(request, user_id=user_id)

    @patch(f"{USER_SERVICE}.get_profile")
    def test_get_profile_returns_200(self, mocked):
        mocked.return_value = _profile_dto(uuid.UUID(self.target_id), "FOLLOWING", True)
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["relationship"]["status"], "FOLLOWING")
        mocked.assert_called_once_with(
            viewer_id=self.caller_id, target_user_id=self.target_id
        )

    @patch(f"{USER_SERVICE}.get_profile")
    def test_blocked_viewer_returns_404(self, mocked):
        mocked.side_effect = UserBlockedException(self.target_id)
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{USER_SERVICE}.get_profile")
    def test_missing_user_returns_404(self, mocked):
        mocked.side_effect = UserNotFoundException()
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
