import json
import uuid
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework import status

from backend.dto.post_like_dto import LikeStateDTO
from backend.exceptions.post_exception import PostNotFoundException
from backend.views.post_like import PostLikeView

SERVICE = "backend.views.post_like.PostLikeService"


class PostLikeViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.post_id = str(uuid.uuid4())

    def _post(self, post_id):
        request = self.factory.post(
            "/v1/posts/x/like",
            data=json.dumps({}),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return PostLikeView.as_view()(request, post_id=post_id)

    def _delete(self, post_id):
        request = self.factory.delete("/v1/posts/x/like")
        request.user_id = self.caller_id
        return PostLikeView.as_view()(request, post_id=post_id)

    @patch(f"{SERVICE}.like")
    def test_like_returns_200_with_state(self, mocked):
        mocked.return_value = LikeStateDTO(liked=True, likeCount=3)

        response = self._post(self.post_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["liked"], True)
        self.assertEqual(response.data["data"]["likeCount"], 3)
        mocked.assert_called_once_with(user_id=self.caller_id, post_id=self.post_id)

    @patch(f"{SERVICE}.unlike")
    def test_unlike_returns_200_with_state(self, mocked):
        mocked.return_value = LikeStateDTO(liked=False, likeCount=2)

        response = self._delete(self.post_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["liked"], False)
        self.assertEqual(response.data["data"]["likeCount"], 2)

    @patch(f"{SERVICE}.like")
    def test_like_invalid_uuid_returns_400(self, mocked):
        response = self._post("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mocked.assert_not_called()

    @patch(f"{SERVICE}.unlike")
    def test_unlike_invalid_uuid_returns_400(self, mocked):
        response = self._delete("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mocked.assert_not_called()

    @patch(f"{SERVICE}.like")
    def test_like_missing_post_returns_404(self, mocked):
        mocked.side_effect = PostNotFoundException(post_id=self.post_id)

        response = self._post(self.post_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.unlike")
    def test_unlike_missing_post_returns_404(self, mocked):
        mocked.side_effect = PostNotFoundException(post_id=self.post_id)

        response = self._delete(self.post_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.like")
    def test_like_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")

        response = self._post(self.post_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
