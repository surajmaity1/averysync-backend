from unittest.mock import patch

from django.test import SimpleTestCase

from backend.dto.post_like_dto import LikeStateDTO
from backend.exceptions.post_exception import PostNotFoundException
from backend.services.post_like_service import PostLikeService

USER_ID = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"
POST_ID = "28cbefee-136e-4a33-b73e-8533599e5222"


class PostLikeServiceTests(SimpleTestCase):
    @patch("backend.services.post_like_service.PostLikeRepository.like")
    def test_like_returns_liked_state_with_count_from_repository(self, mock_like):
        mock_like.return_value = 5

        result = PostLikeService.like(user_id=USER_ID, post_id=POST_ID)

        self.assertIsInstance(result, LikeStateDTO)
        self.assertTrue(result.liked)
        self.assertEqual(result.likeCount, 5)

    @patch("backend.services.post_like_service.PostLikeRepository.like")
    def test_like_passes_identifiers_to_repository(self, mock_like):
        mock_like.return_value = 1

        PostLikeService.like(user_id=USER_ID, post_id=POST_ID)

        _, kwargs = mock_like.call_args
        self.assertEqual(kwargs["user_id"], USER_ID)
        self.assertEqual(kwargs["post_id"], POST_ID)

    @patch("backend.services.post_like_service.PostLikeRepository.like")
    def test_like_raises_not_found_when_post_missing(self, mock_like):
        mock_like.return_value = None

        with self.assertRaises(PostNotFoundException):
            PostLikeService.like(user_id=USER_ID, post_id=POST_ID)

    @patch("backend.services.post_like_service.PostLikeRepository.unlike")
    def test_unlike_returns_unliked_state_with_count_from_repository(self, mock_unlike):
        mock_unlike.return_value = 4

        result = PostLikeService.unlike(user_id=USER_ID, post_id=POST_ID)

        self.assertIsInstance(result, LikeStateDTO)
        self.assertFalse(result.liked)
        self.assertEqual(result.likeCount, 4)

    @patch("backend.services.post_like_service.PostLikeRepository.unlike")
    def test_unlike_raises_not_found_when_post_missing(self, mock_unlike):
        mock_unlike.return_value = None

        with self.assertRaises(PostNotFoundException):
            PostLikeService.unlike(user_id=USER_ID, post_id=POST_ID)
