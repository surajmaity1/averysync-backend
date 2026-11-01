from django.test import TestCase

from backend.models.post import PostModel
from backend.models.post_like import PostLikeModel
from backend.repositories.post_like_repository import PostLikeRepository
from backend.tests.factories import (
    NOW,
    create_post,
    create_post_like,
    create_space,
    create_user,
)


class PostLikeRepositoryTests(TestCase):
    def setUp(self):
        self.author = create_user()
        self.liker = create_user()
        self.post = create_post(created_by=str(self.author.id))

    def _like_count(self) -> int:
        return PostModel.objects.get(id=self.post.id).like_count

    def _active_likes(self) -> int:
        return PostLikeModel.objects.filter(post=self.post, is_deleted=False).count()

    def test_like_creates_active_row_and_returns_count_one(self):
        count = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )

        self.assertEqual(count, 1)
        self.assertEqual(self._like_count(), 1)
        self.assertEqual(self._active_likes(), 1)

    def test_like_is_idempotent_and_does_not_double_count(self):
        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )
        count = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )

        self.assertEqual(count, 1)
        self.assertEqual(self._like_count(), 1)
        self.assertEqual(self._active_likes(), 1)

    def test_like_reactivates_a_soft_deleted_like(self):
        create_post_like(self.post, self.liker, is_deleted=True)

        count = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )

        self.assertEqual(count, 1)
        self.assertEqual(self._active_likes(), 1)
        self.assertEqual(
            PostLikeModel.objects.filter(post=self.post, user=self.liker).count(),
            1,
        )

    def test_like_on_missing_post_returns_none(self):
        missing_post_id = "11111111-1111-1111-1111-111111111111"

        result = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=missing_post_id, now=NOW
        )

        self.assertIsNone(result)

    def test_like_on_deleted_post_returns_none(self):
        deleted = create_post(created_by=str(self.author.id), is_deleted=True)

        result = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(deleted.id), now=NOW
        )

        self.assertIsNone(result)

    def test_two_users_liking_same_post_counts_both(self):
        other = create_user()

        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )
        count = PostLikeRepository.like(
            user_id=str(other.id), post_id=str(self.post.id), now=NOW
        )

        self.assertEqual(count, 2)
        self.assertEqual(self._like_count(), 2)

    def test_unlike_soft_deletes_and_decrements_to_zero(self):
        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )

        count = PostLikeRepository.unlike(
            user_id=str(self.liker.id), post_id=str(self.post.id)
        )

        self.assertEqual(count, 0)
        self.assertEqual(self._like_count(), 0)
        self.assertEqual(self._active_likes(), 0)

    def test_unlike_when_not_liked_is_a_noop_and_never_negative(self):
        count = PostLikeRepository.unlike(
            user_id=str(self.liker.id), post_id=str(self.post.id)
        )

        self.assertEqual(count, 0)
        self.assertEqual(self._like_count(), 0)

    def test_unlike_on_missing_post_returns_none(self):
        missing_post_id = "22222222-2222-2222-2222-222222222222"

        result = PostLikeRepository.unlike(
            user_id=str(self.liker.id), post_id=missing_post_id
        )

        self.assertIsNone(result)

    def test_is_liked_reflects_active_state(self):
        self.assertFalse(
            PostLikeRepository.is_liked(
                user_id=str(self.liker.id), post_id=str(self.post.id)
            )
        )

        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )
        self.assertTrue(
            PostLikeRepository.is_liked(
                user_id=str(self.liker.id), post_id=str(self.post.id)
            )
        )

        PostLikeRepository.unlike(user_id=str(self.liker.id), post_id=str(self.post.id))
        self.assertFalse(
            PostLikeRepository.is_liked(
                user_id=str(self.liker.id), post_id=str(self.post.id)
            )
        )

    def test_like_works_for_a_space_post_type(self):
        space = create_space(created_by=str(self.author.id))

        count = PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(space.id), now=NOW
        )

        self.assertEqual(count, 1)
        self.assertEqual(PostModel.objects.get(id=space.id).like_count, 1)

    def test_liked_post_ids_returns_only_actively_liked(self):
        post_b = create_post(created_by=str(self.author.id))
        post_c = create_post(created_by=str(self.author.id))
        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(self.post.id), now=NOW
        )
        PostLikeRepository.like(
            user_id=str(self.liker.id), post_id=str(post_b.id), now=NOW
        )
        PostLikeRepository.unlike(user_id=str(self.liker.id), post_id=str(post_b.id))

        liked = PostLikeRepository.liked_post_ids(
            user_id=str(self.liker.id),
            post_ids=[str(self.post.id), str(post_b.id), str(post_c.id)],
        )

        self.assertEqual(liked, {str(self.post.id)})

    def test_liked_post_ids_with_empty_input_returns_empty_set(self):
        self.assertEqual(
            PostLikeRepository.liked_post_ids(user_id=str(self.liker.id), post_ids=[]),
            set(),
        )
