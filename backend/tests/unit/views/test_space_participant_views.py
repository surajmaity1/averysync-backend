import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from backend.dto.responses.get_participants_response import GetParticipantsResponse
from backend.dto.responses.join_space_response import JoinSpaceResponse
from backend.dto.space_participant_dto import ParticipantDTO
from backend.exceptions.participant_exception import (
    ModerationForbiddenException,
    ParticipantNotFoundException,
    SelfMuteNotAllowedException,
    SpaceEndedException,
    SpaceNotLiveException,
)
from backend.exceptions.post_exception import SpaceNotFoundException
from backend.views.space_participant import (
    ParticipantDetailView,
    ParticipantMuteView,
    ParticipantsView,
)

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
SERVICE = "backend.views.space_participant.SpaceParticipantService"


def _participant_dto(
    space_id: str, user_id: str, role: str = "LISTENER", is_muted: bool = False
) -> ParticipantDTO:
    return ParticipantDTO(
        id=uuid.uuid4(),
        spaceId=space_id,
        userId=user_id,
        role=role,
        isMuted=is_muted,
        mutedUntil=None,
        firstJoinedAt=NOW,
        lastJoinedAt=NOW,
        leftAt=None,
    )


class ParticipantsViewJoinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.space_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def _post(self, space_id: str):
        url = reverse("posts_participants", kwargs={"space_id": space_id})
        request = self.factory.post(
            url, data=json.dumps({}), content_type="application/json"
        )
        request.user_id = self.user_id
        request.user_email = "user@example.com"
        return ParticipantsView.as_view()(request, space_id=space_id)

    @patch(f"{SERVICE}.join")
    def test_first_join_returns_201_with_data_and_token(self, mocked_join):
        dto = _participant_dto(self.space_id, self.user_id)
        mocked_join.return_value = (
            JoinSpaceResponse(data=dto, token="the-token"),
            True,
        )

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["token"], "the-token")
        self.assertEqual(response.data["data"]["userId"], self.user_id)
        mocked_join.assert_called_once_with(
            space_id=self.space_id, user_id=self.user_id
        )

    @patch(f"{SERVICE}.join")
    def test_rejoin_returns_200(self, mocked_join):
        dto = _participant_dto(self.space_id, self.user_id)
        mocked_join.return_value = (
            JoinSpaceResponse(data=dto, token="the-token"),
            False,
        )

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_space_uuid_returns_400(self):
        response = self._post("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.join")
    def test_space_not_found_returns_404(self, mocked_join):
        mocked_join.side_effect = SpaceNotFoundException(space_id=self.space_id)

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.join")
    def test_space_not_live_returns_409(self, mocked_join):
        mocked_join.side_effect = SpaceNotLiveException(space_id=self.space_id)

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch(f"{SERVICE}.join")
    def test_space_ended_returns_410(self, mocked_join):
        mocked_join.side_effect = SpaceEndedException(space_id=self.space_id)

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    @patch(f"{SERVICE}.join")
    def test_unexpected_error_returns_500(self, mocked_join):
        mocked_join.side_effect = RuntimeError("boom")

        response = self._post(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParticipantsViewListTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.space_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    def _get(self, space_id: str, query: str = ""):
        url = reverse("posts_participants", kwargs={"space_id": space_id}) + query
        request = self.factory.get(url)
        request.user_id = self.user_id
        request.user_email = "user@example.com"
        return ParticipantsView.as_view()(request, space_id=space_id)

    @patch(f"{SERVICE}.get_participants")
    def test_list_returns_200_with_participants(self, mocked_get):
        dto = _participant_dto(self.space_id, self.user_id)
        mocked_get.return_value = GetParticipantsResponse(data=[dto])

        response = self._get(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        mocked_get.assert_called_once_with(space_id=self.space_id, include_left=False)

    @patch(f"{SERVICE}.get_participants")
    def test_list_returns_200_empty(self, mocked_get):
        mocked_get.return_value = GetParticipantsResponse(data=[])

        response = self._get(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])

    @patch(f"{SERVICE}.get_participants")
    def test_include_left_query_param_passed_through(self, mocked_get):
        mocked_get.return_value = GetParticipantsResponse(data=[])

        self._get(self.space_id, query="?includeLeft=true")

        mocked_get.assert_called_once_with(space_id=self.space_id, include_left=True)

    def test_bad_space_uuid_returns_400(self):
        response = self._get("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.get_participants")
    def test_space_not_found_returns_404(self, mocked_get):
        mocked_get.side_effect = SpaceNotFoundException(space_id=self.space_id)

        response = self._get(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.get_participants")
    def test_unexpected_error_returns_500(self, mocked_get):
        mocked_get.side_effect = RuntimeError("boom")

        response = self._get(self.space_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParticipantDetailViewDeleteTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.space_id = str(uuid.uuid4())
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _delete(self, space_id: str, user_id: str):
        url = reverse(
            "posts_participant_detail",
            kwargs={"space_id": space_id, "user_id": user_id},
        )
        request = self.factory.delete(url)
        request.user_id = self.caller_id
        request.user_email = "user@example.com"
        return ParticipantDetailView.as_view()(
            request, space_id=space_id, user_id=user_id
        )

    @patch(f"{SERVICE}.leave_or_remove")
    def test_self_leave_returns_204(self, mocked_leave):
        mocked_leave.return_value = None

        response = self._delete(self.space_id, self.caller_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_leave.assert_called_once_with(
            space_id=self.space_id,
            target_user_id=self.caller_id,
            caller_id=self.caller_id,
        )

    @patch(f"{SERVICE}.leave_or_remove")
    def test_host_remove_returns_204(self, mocked_leave):
        mocked_leave.return_value = None

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_bad_space_uuid_returns_400(self):
        response = self._delete("not-a-uuid", self.target_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_user_uuid_returns_400(self):
        response = self._delete(self.space_id, "not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_participant_not_found_returns_404(self, mocked_leave):
        mocked_leave.side_effect = ParticipantNotFoundException(
            user_id=self.target_id, space_id=self.space_id
        )

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_space_not_found_returns_404(self, mocked_leave):
        mocked_leave.side_effect = SpaceNotFoundException(space_id=self.space_id)

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_not_host_returns_403(self, mocked_leave):
        mocked_leave.side_effect = ModerationForbiddenException(space_id=self.space_id)

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_space_not_live_returns_409(self, mocked_leave):
        mocked_leave.side_effect = SpaceNotLiveException(space_id=self.space_id)

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_space_ended_returns_410(self, mocked_leave):
        mocked_leave.side_effect = SpaceEndedException(space_id=self.space_id)

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    @patch(f"{SERVICE}.leave_or_remove")
    def test_unexpected_error_returns_500(self, mocked_leave):
        mocked_leave.side_effect = RuntimeError("boom")

        response = self._delete(self.space_id, self.target_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ParticipantMuteViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.space_id = str(uuid.uuid4())
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _patch(self, space_id: str, user_id: str, body: dict):
        url = reverse(
            "posts_participant_mute",
            kwargs={"space_id": space_id, "user_id": user_id},
        )
        request = self.factory.patch(
            url, data=json.dumps(body), content_type="application/json"
        )
        request.user_id = self.caller_id
        request.user_email = "user@example.com"
        return ParticipantMuteView.as_view()(
            request, space_id=space_id, user_id=user_id
        )

    @patch(f"{SERVICE}.set_mute_state")
    def test_mute_returns_200_with_updated_dto(self, mocked_mute):
        dto = _participant_dto(self.space_id, self.target_id, is_muted=True)
        mocked_mute.return_value = dto

        response = self._patch(
            self.space_id,
            self.target_id,
            {"isMuted": True, "durationSeconds": 600, "reason": "noise"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["isMuted"])
        args, kwargs = mocked_mute.call_args
        self.assertEqual(kwargs["space_id"], self.space_id)
        self.assertEqual(kwargs["target_user_id"], self.target_id)
        self.assertEqual(kwargs["caller_id"], self.caller_id)
        self.assertTrue(kwargs["dto"].isMuted)
        self.assertEqual(kwargs["dto"].durationSeconds, 600)
        self.assertEqual(kwargs["dto"].reason, "noise")

    @patch(f"{SERVICE}.set_mute_state")
    def test_unmute_returns_200(self, mocked_mute):
        dto = _participant_dto(self.space_id, self.target_id, is_muted=False)
        mocked_mute.return_value = dto

        response = self._patch(self.space_id, self.target_id, {"isMuted": False})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["isMuted"])

    def test_bad_space_uuid_returns_400(self):
        response = self._patch("not-a-uuid", self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_user_uuid_returns_400(self):
        response = self._patch(self.space_id, "not-a-uuid", {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_ismuted_returns_400(self):
        response = self._patch(self.space_id, self.target_id, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duration_out_of_range_returns_400(self):
        response = self._patch(
            self.space_id,
            self.target_id,
            {"isMuted": True, "durationSeconds": 999999},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mute_fields_with_unmute_returns_400(self):
        response = self._patch(
            self.space_id,
            self.target_id,
            {"isMuted": False, "durationSeconds": 600},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.set_mute_state")
    def test_self_mute_returns_400(self, mocked_mute):
        mocked_mute.side_effect = SelfMuteNotAllowedException()

        response = self._patch(self.space_id, self.caller_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.set_mute_state")
    def test_not_host_returns_403(self, mocked_mute):
        mocked_mute.side_effect = ModerationForbiddenException(space_id=self.space_id)

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(f"{SERVICE}.set_mute_state")
    def test_participant_not_found_returns_404(self, mocked_mute):
        mocked_mute.side_effect = ParticipantNotFoundException(
            user_id=self.target_id, space_id=self.space_id
        )

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.set_mute_state")
    def test_space_not_found_returns_404(self, mocked_mute):
        mocked_mute.side_effect = SpaceNotFoundException(space_id=self.space_id)

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.set_mute_state")
    def test_space_not_live_returns_409(self, mocked_mute):
        mocked_mute.side_effect = SpaceNotLiveException(space_id=self.space_id)

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch(f"{SERVICE}.set_mute_state")
    def test_space_ended_returns_410(self, mocked_mute):
        mocked_mute.side_effect = SpaceEndedException(space_id=self.space_id)

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_410_GONE)

    @patch(f"{SERVICE}.set_mute_state")
    def test_unexpected_error_returns_500(self, mocked_mute):
        mocked_mute.side_effect = RuntimeError("boom")

        response = self._patch(self.space_id, self.target_id, {"isMuted": True})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
