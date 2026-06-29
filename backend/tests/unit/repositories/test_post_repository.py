from unittest import TestCase
from unittest.mock import patch
from backend.tests.fixtures.post import posts_data
from backend.models.post import PostModel
from backend.repositories.post_repository import PostRepository


class PostRepositoryTests(TestCase):
    def setUp(self):
        self.post_data = posts_data[0].copy()
        self.post = PostModel(
            title=self.post_data["title"],
            created_at=self.post_data["createdAt"],
            created_by=self.post_data["createdBy"],
        )

    @patch("backend.repositories.post_repository.PostRepository.create")
    def test_create_post_success(self, mock_create):
        post = self.post
        expected_post = post
        mock_create.return_value = expected_post

        response = PostRepository.create(post)
        self.assertEqual(response, expected_post)
        self.assertEqual(response.id, expected_post.id)
        mock_create.assert_called_once_with(post)
