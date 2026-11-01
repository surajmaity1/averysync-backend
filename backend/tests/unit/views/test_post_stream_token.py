import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import jwt
from django.test import RequestFactory, TestCase, override_settings
from rest_framework import status
from rest_framework.reverse import reverse

from backend.constants.post import PostType, SpaceStatus
from backend.dto.post_dto import PostDTO
from backend.views.post import PostDetailView

FAR_FUTURE = datetime(2999, 1, 1, tzinfo=timezone.utc)


def _live_space_dto(created_by: str) -> PostDTO:
    return PostDTO(
        id=uuid.uuid4(),
        title="BLR Meetup",
        description="HSR Layout",
        type=PostType.SPACE,
        isRecorded=True,
        status=SpaceStatus.LIVE,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        createdBy=created_by,
    )


def _scheduled_space_dto(created_by: str) -> PostDTO:
    dto = _live_space_dto(created_by=created_by)
    dto.status = SpaceStatus.SCHEDULED
    return dto


@override_settings(
    STREAM_API_SECRET_KEY="a-real-secret",
    WEBRTC_ISSUER="backend-webrtc-issuer",
    WEBRTC_AUDIENCE="stream-go-service",
)
class PostDetailStreamTokenTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user_id = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"
        self.post_dto = _live_space_dto(created_by=self.user_id)

    def _authenticated_get(self, url):
        request = self.factory.get(url)
        request.user_id = self.user_id
        request.user_email = "user@example.com"
        return request

    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_stream_token_includes_configured_audience_claim(
        self, mocked_get_post, mocked_ensure
    ):
        mocked_get_post.return_value = self.post_dto
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["token"]
        self.assertIsNotNone(token)

        decoded = jwt.decode(
            token,
            "a-real-secret",
            algorithms=["HS256"],
            audience="stream-go-service",
        )
        self.assertEqual(decoded["aud"], "stream-go-service")
        self.assertEqual(decoded["iss"], "backend-webrtc-issuer")

    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_stream_token_rejected_by_consumer_expecting_different_audience(
        self, mocked_get_post, mocked_ensure
    ):
        mocked_get_post.return_value = self.post_dto
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))
        token = response.data["token"]

        with self.assertRaises(jwt.InvalidAudienceError):
            jwt.decode(
                token,
                "a-real-secret",
                algorithms=["HS256"],
                audience="some-other-service",
            )

    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_joining_live_space_creates_participant_record(
        self, mocked_get_post, mocked_ensure
    ):
        listener_id = str(uuid.uuid4())
        self.post_dto = _live_space_dto(created_by=str(uuid.uuid4()))
        mocked_get_post.return_value = self.post_dto
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self.factory.get(url)
        request.user_id = listener_id
        request.user_email = "listener@example.com"

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_ensure.assert_called_once_with(
            space_id=str(self.post_dto.id),
            user_id=listener_id,
            created_by=str(self.post_dto.createdBy),
        )

    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_non_live_space_does_not_create_participant_record(
        self, mocked_get_post, mocked_ensure
    ):
        scheduled = _scheduled_space_dto(created_by=self.user_id)
        mocked_get_post.return_value = scheduled
        url = reverse("post_detail", kwargs={"post_id": str(scheduled.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(scheduled.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data.get("token"))
        mocked_ensure.assert_not_called()

    @patch(
        "backend.views.post.SpaceParticipantService.ensure_active_participant",
        side_effect=ValueError("participant write failed"),
    )
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_join_still_issues_token_when_participant_write_fails(
        self, mocked_get_post, mocked_ensure
    ):
        mocked_get_post.return_value = self.post_dto
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["token"])

    @patch("backend.views.post.SpaceParticipantService.effective_mute_claims")
    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_stream_token_carries_effective_mute_for_muted_participant(
        self, mocked_get_post, mocked_ensure, mocked_mute_claims
    ):
        mocked_get_post.return_value = self.post_dto
        mocked_mute_claims.return_value = (True, int(FAR_FUTURE.timestamp()))
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))

        decoded = jwt.decode(
            response.data["token"],
            "a-real-secret",
            algorithms=["HS256"],
            audience="stream-go-service",
        )
        self.assertEqual(decoded.get("is_muted"), True)
        self.assertEqual(decoded.get("muted_until"), int(FAR_FUTURE.timestamp()))
        mocked_mute_claims.assert_called_once_with(
            space_id=str(self.post_dto.id), user_id=self.user_id
        )

    @patch("backend.views.post.SpaceParticipantService.effective_mute_claims")
    @patch("backend.views.post.SpaceParticipantService.ensure_active_participant")
    @patch("backend.views.post.PostService.get_post_by_id")
    def test_stream_token_marks_unmuted_participant_not_muted(
        self, mocked_get_post, mocked_ensure, mocked_mute_claims
    ):
        mocked_get_post.return_value = self.post_dto
        mocked_mute_claims.return_value = (False, None)
        url = reverse("post_detail", kwargs={"post_id": str(self.post_dto.id)})
        request = self._authenticated_get(url)

        response = PostDetailView.as_view()(request, post_id=str(self.post_dto.id))

        decoded = jwt.decode(
            response.data["token"],
            "a-real-secret",
            algorithms=["HS256"],
            audience="stream-go-service",
        )
        self.assertEqual(decoded.get("is_muted"), False)
        self.assertIsNone(decoded.get("muted_until"))
