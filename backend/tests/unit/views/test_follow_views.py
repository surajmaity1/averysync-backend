import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import resolve, reverse
from rest_framework import status

from backend.dto.follow_dto import FollowDTO, FollowUserDTO
from backend.dto.responses.get_followers_response import GetFollowersResponse
from backend.dto.responses.get_follow_requests_response import (
    GetFollowRequestsResponse,
)
from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import (
    CannotFollowSelfException,
    FollowerNotFoundException,
    FollowForbiddenException,
    FollowRequestNotFoundException,
    NotFollowingException,
    UserBlockedException,
)
from backend.views.follow import (
    FollowersView,
    FollowingView,
    FollowRequestActionView,
    FollowRequestsView,
    FollowerRemoveView,
    FollowView,
)

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
SERVICE = "backend.views.follow.FollowService"


def _follow_dto(follower_id, followee_id, status_name="ACCEPTED"):
    return FollowDTO(
        id=uuid.uuid4(),
        followerId=follower_id,
        followeeId=followee_id,
        status=status_name,
        requestedAt=NOW,
        respondedAt=NOW if status_name == "ACCEPTED" else None,
        createdAt=NOW,
    )


class FollowViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _post(self, user_id):
        request = self.factory.post(
            "/v1/users/x/follow", data=json.dumps({}), content_type="application/json"
        )
        request.user_id = self.caller_id
        return FollowView.as_view()(request, user_id=user_id)

    def _delete(self, user_id):
        request = self.factory.delete("/v1/users/x/follow")
        request.user_id = self.caller_id
        return FollowView.as_view()(request, user_id=user_id)

    @patch(f"{SERVICE}.follow")
    def test_follow_new_returns_201(self, mocked):
        mocked.return_value = (
            _follow_dto(self.caller_id, self.target_id),
            True,
        )
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["followeeId"], self.target_id)

    @patch(f"{SERVICE}.follow")
    def test_follow_existing_returns_200(self, mocked):
        mocked.return_value = (
            _follow_dto(self.caller_id, self.target_id),
            False,
        )
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(f"{SERVICE}.follow")
    def test_follow_self_returns_400(self, mocked):
        mocked.side_effect = CannotFollowSelfException()
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.follow")
    def test_follow_blocked_returns_404(self, mocked):
        mocked.side_effect = UserBlockedException(self.target_id)
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.follow")
    def test_follow_missing_target_returns_404(self, mocked):
        mocked.side_effect = UserNotFoundException()
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_follow_bad_uuid_returns_400(self):
        response = self._post("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.follow")
    def test_follow_accepts_uuid_object_from_path_converter(self, mocked):
        # The `<uuid:user_id>` route converter hands the view a uuid.UUID
        # instance, not a string. Regression for the 500 crash where
        # validate_uuid() called uuid.UUID() on an already-parsed UUID.
        target = uuid.UUID(self.target_id)
        mocked.return_value = (_follow_dto(self.caller_id, self.target_id), True)
        response = self._post(target)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{SERVICE}.unfollow_or_cancel")
    def test_unfollow_returns_204(self, mocked):
        mocked.return_value = None
        response = self._delete(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(f"{SERVICE}.unfollow_or_cancel")
    def test_unfollow_not_following_returns_404(self, mocked):
        mocked.side_effect = NotFollowingException(self.target_id)
        response = self._delete(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unfollow_bad_uuid_returns_400(self):
        response = self._delete("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.follow")
    def test_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class FollowersViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _get(self, user_id, query=""):
        request = self.factory.get(f"/v1/users/x/followers{query}")
        request.user_id = self.caller_id
        return FollowersView.as_view()(request, user_id=user_id)

    @patch(f"{SERVICE}.get_followers")
    def test_list_returns_200(self, mocked):
        mocked.return_value = GetFollowersResponse(
            data=[FollowUserDTO(id=uuid.uuid4(), name="Ada", followedAt=NOW)],
            total=1,
            limit=20,
            offset=0,
        )
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    @patch(f"{SERVICE}.get_followers")
    def test_private_forbidden_returns_403(self, mocked):
        mocked.side_effect = FollowForbiddenException(self.target_id)
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(f"{SERVICE}.get_followers")
    def test_blocked_viewer_returns_404(self, mocked):
        mocked.side_effect = UserBlockedException(self.target_id)
        response = self._get(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bad_uuid_returns_400(self):
        response = self._get("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_pagination_returns_400(self):
        response = self._get(self.target_id, query="?limit=0")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FollowingViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    @patch(f"{SERVICE}.get_following")
    def test_list_returns_200(self, mocked):
        from backend.dto.responses.get_following_response import (
            GetFollowingResponse,
        )

        mocked.return_value = GetFollowingResponse(data=[], total=0, limit=20, offset=0)
        request = self.factory.get("/v1/users/x/following")
        request.user_id = self.caller_id
        response = FollowingView.as_view()(request, user_id=self.target_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(f"{SERVICE}.get_following")
    def test_private_forbidden_returns_403(self, mocked):
        mocked.side_effect = FollowForbiddenException(self.target_id)
        request = self.factory.get("/v1/users/x/following")
        request.user_id = self.caller_id
        response = FollowingView.as_view()(request, user_id=self.target_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_pagination_returns_400(self):
        request = self.factory.get("/v1/users/x/following?limit=0")
        request.user_id = self.caller_id
        response = FollowingView.as_view()(request, user_id=self.target_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_uuid_returns_400(self):
        request = self.factory.get("/v1/users/x/following")
        request.user_id = self.caller_id
        response = FollowingView.as_view()(request, user_id="not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FollowRequestsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    @patch(f"{SERVICE}.get_requests")
    def test_returns_200(self, mocked):
        mocked.return_value = GetFollowRequestsResponse(
            data=[FollowUserDTO(id=uuid.uuid4(), name="Bob")],
            total=1,
            limit=20,
            offset=0,
        )
        request = self.factory.get("/v1/requests/follow")
        request.user_id = self.caller_id
        response = FollowRequestsView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    def test_invalid_pagination_returns_400(self):
        request = self.factory.get("/v1/requests/follow?offset=-1")
        request.user_id = self.caller_id
        response = FollowRequestsView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.get_requests")
    def test_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        request = self.factory.get("/v1/requests/follow")
        request.user_id = self.caller_id
        response = FollowRequestsView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class FollowRequestActionViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.follower_id = str(uuid.uuid4())

    def _patch(self, follower_id, data):
        request = self.factory.patch(
            f"/v1/requests/follow/{follower_id}",
            data=json.dumps(data),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return FollowRequestActionView.as_view()(request, follower_id=follower_id)

    @patch(f"{SERVICE}.accept")
    def test_accept_returns_200(self, mocked):
        mocked.return_value = _follow_dto(self.follower_id, self.caller_id)
        response = self._patch(self.follower_id, {"action": "accept"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked.assert_called_once_with(
            followee_id=self.caller_id, follower_id=self.follower_id
        )

    @patch(f"{SERVICE}.accept")
    def test_accept_not_found_returns_404(self, mocked):
        mocked.side_effect = FollowRequestNotFoundException(self.follower_id)
        response = self._patch(self.follower_id, {"action": "accept"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.reject")
    def test_reject_returns_200(self, mocked):
        mocked.return_value = None
        response = self._patch(self.follower_id, {"action": "reject"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked.assert_called_once_with(
            followee_id=self.caller_id, follower_id=self.follower_id
        )

    @patch(f"{SERVICE}.reject")
    def test_reject_not_found_returns_404(self, mocked):
        mocked.side_effect = FollowRequestNotFoundException(self.follower_id)
        response = self._patch(self.follower_id, {"action": "reject"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_action_returns_400(self):
        response = self._patch(self.follower_id, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_action_returns_400(self):
        response = self._patch(self.follower_id, {"action": "unknown"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_field_returns_400(self):
        response = self._patch(
            self.follower_id, {"action": "accept", "extra": "invalid"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_uuid_returns_400(self):
        response = self._patch("not-a-uuid", {"action": "accept"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_method_not_allowed(self):
        request = self.factory.post(
            f"/v1/requests/follow/{self.follower_id}",
            data=json.dumps({"action": "accept"}),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        response = FollowRequestActionView.as_view()(
            request, follower_id=self.follower_id
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_url_resolves_to_view(self):
        url = reverse("follow_request_action", kwargs={"follower_id": self.follower_id})
        match = resolve(url)
        self.assertEqual(match.func.view_class, FollowRequestActionView)


class FollowerRemoveViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.follower_id = str(uuid.uuid4())

    def _delete(self, follower_id):
        request = self.factory.delete("/v1/followers/x")
        request.user_id = self.caller_id
        return FollowerRemoveView.as_view()(request, follower_id=follower_id)

    @patch(f"{SERVICE}.remove_follower")
    def test_remove_returns_204(self, mocked):
        mocked.return_value = None
        response = self._delete(self.follower_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(f"{SERVICE}.remove_follower")
    def test_not_found_returns_404(self, mocked):
        mocked.side_effect = FollowerNotFoundException(self.follower_id)
        response = self._delete(self.follower_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bad_uuid_returns_400(self):
        response = self._delete("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
