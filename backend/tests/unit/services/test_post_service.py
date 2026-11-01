import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from backend.constants.messages import ApiErrors
from backend.constants.post import PostType, SpaceStatus
from backend.dto.post_dto import CreatePostDTO, PostDTO
from backend.dto.responses.create_post_response import CreatePostResponse
from backend.dto.responses.error_response import ApiErrorResponse
from backend.dto.responses.get_posts_response import GetPostsResponse
from backend.exceptions.post_exception import (
    PostAlreadyDeletedException,
    PostNotFoundException,
    PostUpdateForbidden,
)
from backend.models.post import PostModel
from backend.services.post_service import PostService


def build_post_model(**overrides) -> PostModel:
    """An in-memory PostModel (never saved) with sensible defaults for DTO mapping."""
    defaults = dict(
        id=uuid.uuid4(),
        title="BLR Meetup",
        description="HSR Layout",
        type=PostType.SPACE.name,
        is_recorded=True,
        scheduled_started_at=None,
        scheduled_ended_at=None,
        started_at=None,
        ended_at=None,
        created_in_timezone="Asia/Kolkata",
        status=PostModel.SpaceStatus.SCHEDULED,
        created_at=datetime(2026, 6, 6, 14, 9, 55, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 9, 11, 31, 48, tzinfo=timezone.utc),
        created_by="9dee2457-9d0b-4bd8-a509-abaaaf618cfa",
        updated_by=None,
    )
    defaults.update(overrides)
    return PostModel(**defaults)


class PreparePostDTOTests(TestCase):
    def test_maps_model_fields_to_camel_case_dto(self):
        model = build_post_model()

        dto = PostService._prepare_post_dto(model)

        self.assertIsInstance(dto, PostDTO)
        self.assertEqual(dto.id, model.id)
        self.assertEqual(dto.title, model.title)
        self.assertEqual(dto.description, model.description)
        self.assertEqual(dto.type, PostType.SPACE)
        self.assertEqual(dto.isRecorded, model.is_recorded)
        self.assertEqual(dto.createdInTimezone, model.created_in_timezone)
        self.assertEqual(dto.status, SpaceStatus.SCHEDULED)
        self.assertEqual(dto.createdAt, model.created_at)
        self.assertEqual(dto.updatedAt, model.updated_at)
        self.assertEqual(dto.createdBy, model.created_by)
        self.assertIsNone(dto.updatedBy)

    def test_maps_plain_post_with_null_status(self):
        model = build_post_model(type=PostType.POST.name, status=None)

        dto = PostService._prepare_post_dto(model)

        self.assertEqual(dto.type, PostType.POST)
        self.assertIsNone(dto.status)


class CreatePostTests(TestCase):
    def setUp(self):
        self.user_id = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"

    @patch("backend.services.post_service.PostRepository.create")
    def test_create_space_sets_scheduled_status(self, mock_create):
        # Echo the model back so we can inspect what the service built.
        mock_create.side_effect = lambda post: post
        dto = CreatePostDTO(
            title="BLR Meetup",
            description="HSR Layout",
            type=PostType.SPACE,
            isRecorded=True,
            created_by=self.user_id,
        )

        response = PostService.create_post(dto)

        self.assertIsInstance(response, CreatePostResponse)
        mock_create.assert_called_once()
        built_post = mock_create.call_args.args[0]
        self.assertEqual(built_post.type, "SPACE")
        self.assertEqual(built_post.status, PostModel.SpaceStatus.SCHEDULED)
        self.assertEqual(built_post.created_by, self.user_id)
        self.assertEqual(response.data.title, "BLR Meetup")

    @patch("backend.services.post_service.PostRepository.create")
    def test_create_plain_post_has_no_status(self, mock_create):
        mock_create.side_effect = lambda post: post
        dto = CreatePostDTO(
            title="Just a post",
            type=PostType.POST,
            created_by=self.user_id,
        )

        PostService.create_post(dto)

        built_post = mock_create.call_args.args[0]
        self.assertEqual(built_post.type, "POST")
        self.assertIsNone(built_post.status)

    @patch("backend.services.post_service.PostRepository.create")
    def test_repository_api_error_response_is_reraised_unchanged(self, mock_create):
        original = ApiErrorResponse(
            statusCode=409, message="conflict", errors="duplicate"
        )
        mock_create.side_effect = ValueError(original)
        dto = CreatePostDTO(title="x", created_by=self.user_id)

        with self.assertRaises(ValueError) as ctx:
            PostService.create_post(dto)

        self.assertIs(ctx.exception.args[0], original)

    @patch("backend.services.post_service.PostRepository.create")
    def test_repository_value_error_wrapped_as_repository_error(self, mock_create):
        mock_create.side_effect = ValueError("db exploded")
        dto = CreatePostDTO(title="x", created_by=self.user_id)

        with self.assertRaises(ValueError) as ctx:
            PostService.create_post(dto)

        error = ctx.exception.args[0]
        self.assertIsInstance(error, ApiErrorResponse)
        self.assertEqual(error.statusCode, 500)
        self.assertEqual(error.message, ApiErrors.REPOSITORY_ERROR)

    @patch("backend.services.post_service.PostRepository.create")
    def test_unexpected_exception_wrapped_as_internal_server_error(self, mock_create):
        mock_create.side_effect = RuntimeError("boom")
        dto = CreatePostDTO(title="x", created_by=self.user_id)

        with self.assertRaises(ValueError) as ctx:
            PostService.create_post(dto)

        error = ctx.exception.args[0]
        self.assertIsInstance(error, ApiErrorResponse)
        self.assertEqual(error.statusCode, 500)
        self.assertEqual(error.message, ApiErrors.INTERNAL_SERVER_ERROR)


class GetPostsTests(TestCase):
    @patch("backend.services.post_service.PostRepository.get_posts")
    def test_returns_mapped_posts(self, mock_get_posts):
        mock_get_posts.return_value = [build_post_model(), build_post_model()]

        response = PostService.get_posts()

        self.assertIsInstance(response, GetPostsResponse)
        self.assertEqual(len(response.posts), 2)
        self.assertIsInstance(response.posts[0], PostDTO)

    @patch("backend.services.post_service.PostRepository.get_posts")
    def test_returns_empty_list_when_no_posts(self, mock_get_posts):
        mock_get_posts.return_value = []

        response = PostService.get_posts()

        self.assertEqual(response.posts, [])

    @patch("backend.services.post_service.PostRepository.get_posts")
    def test_returns_empty_list_on_unexpected_error(self, mock_get_posts):
        mock_get_posts.side_effect = RuntimeError("boom")

        response = PostService.get_posts()

        self.assertIsInstance(response, GetPostsResponse)
        self.assertEqual(response.posts, [])


class GetPostByIdTests(TestCase):
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_returns_dto_when_found(self, mock_get_by_id):
        model = build_post_model()
        mock_get_by_id.return_value = model

        dto = PostService.get_post_by_id(str(model.id))

        self.assertIsInstance(dto, PostDTO)
        self.assertEqual(dto.id, model.id)
        mock_get_by_id.assert_called_once_with(post_id=str(model.id))

    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_raises_value_error_when_not_found(self, mock_get_by_id):
        mock_get_by_id.return_value = None
        post_id = str(uuid.uuid4())

        with self.assertRaises(ValueError) as ctx:
            PostService.get_post_by_id(post_id)

        self.assertIn(post_id, str(ctx.exception))


class PreparePostDTOLikeTests(TestCase):
    def test_maps_like_count_and_defaults_liked_by_me_false(self):
        model = build_post_model(like_count=7)

        dto = PostService._prepare_post_dto(model)

        self.assertEqual(dto.likeCount, 7)
        self.assertFalse(dto.likedByMe)

    def test_sets_liked_by_me_when_passed(self):
        model = build_post_model(like_count=1)

        dto = PostService._prepare_post_dto(model, liked_by_me=True)

        self.assertTrue(dto.likedByMe)


class GetPostsLikeTests(TestCase):
    @patch("backend.services.post_service.PostLikeRepository.liked_post_ids")
    @patch("backend.services.post_service.PostRepository.get_posts")
    def test_marks_liked_posts_for_the_viewer(self, mock_get_posts, mock_liked_ids):
        liked = build_post_model()
        not_liked = build_post_model()
        mock_get_posts.return_value = [liked, not_liked]
        mock_liked_ids.return_value = {str(liked.id)}

        response = PostService.get_posts(viewer_id="viewer-1")

        by_id = {dto.id: dto for dto in response.posts}
        self.assertTrue(by_id[liked.id].likedByMe)
        self.assertFalse(by_id[not_liked.id].likedByMe)
        mock_liked_ids.assert_called_once_with(
            "viewer-1", [str(liked.id), str(not_liked.id)]
        )

    @patch("backend.services.post_service.PostLikeRepository.liked_post_ids")
    @patch("backend.services.post_service.PostRepository.get_posts")
    def test_anonymous_viewer_never_marks_liked(self, mock_get_posts, mock_liked_ids):
        mock_get_posts.return_value = [build_post_model()]

        response = PostService.get_posts()

        self.assertFalse(response.posts[0].likedByMe)
        mock_liked_ids.assert_not_called()


class GetPostByIdLikeTests(TestCase):
    @patch("backend.services.post_service.PostLikeRepository.is_liked")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_reflects_viewer_like_state(self, mock_get_by_id, mock_is_liked):
        model = build_post_model()
        mock_get_by_id.return_value = model
        mock_is_liked.return_value = True

        dto = PostService.get_post_by_id(str(model.id), viewer_id="viewer-1")

        self.assertTrue(dto.likedByMe)
        mock_is_liked.assert_called_once_with(user_id="viewer-1", post_id=str(model.id))


class DeletePostByIdTests(TestCase):
    def setUp(self):
        self.user_id = "owner-id"

    @patch("backend.services.post_service.PostRepository.delete_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_owner_deletes_successfully(self, mock_get_by_id, mock_delete):
        model = build_post_model(created_by=self.user_id, is_deleted=False)
        mock_get_by_id.return_value = model
        mock_delete.return_value = True

        result = PostService.delete_post_by_id(str(model.id), self.user_id)

        self.assertTrue(result)
        mock_delete.assert_called_once_with(post_id=str(model.id))

    @patch("backend.services.post_service.PostRepository.delete_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_returns_false_when_repository_delete_fails(
        self, mock_get_by_id, mock_delete
    ):
        model = build_post_model(created_by=self.user_id, is_deleted=False)
        mock_get_by_id.return_value = model
        mock_delete.return_value = False

        result = PostService.delete_post_by_id(str(model.id), self.user_id)

        self.assertFalse(result)

    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_raises_when_post_not_found(self, mock_get_by_id):
        mock_get_by_id.return_value = None

        with self.assertRaises(PostNotFoundException):
            PostService.delete_post_by_id(str(uuid.uuid4()), self.user_id)

    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_raises_forbidden_for_non_owner(self, mock_get_by_id):
        model = build_post_model(created_by="someone-else", is_deleted=False)
        mock_get_by_id.return_value = model

        with self.assertRaises(PostUpdateForbidden):
            PostService.delete_post_by_id(str(model.id), self.user_id)

    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_raises_when_already_deleted(self, mock_get_by_id):
        model = build_post_model(created_by=self.user_id, is_deleted=True)
        mock_get_by_id.return_value = model

        with self.assertRaises(PostAlreadyDeletedException):
            PostService.delete_post_by_id(str(model.id), self.user_id)


class UpdatePostByIdTests(TestCase):
    def setUp(self):
        self.user_id = "owner-id"

    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_owner_updates_successfully(self, mock_get_by_id, mock_update):
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        updated = build_post_model(created_by=self.user_id, title="New title")
        mock_update.return_value = updated

        dto = PostService.update_post_by_id(
            post_id=str(model.id),
            user_id=self.user_id,
            validated_data={"title": "New title"},
        )

        self.assertIsInstance(dto, PostDTO)
        self.assertEqual(dto.title, "New title")
        mock_update.assert_called_once_with(
            post_id=str(model.id), update_data={"title": "New title"}
        )

    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_non_owner_update_raises_forbidden(self, mock_get_by_id, mock_update):
        model = build_post_model(created_by="someone-else")
        mock_get_by_id.return_value = model

        with self.assertRaises(PostUpdateForbidden):
            PostService.update_post_by_id(
                post_id=str(model.id),
                user_id=self.user_id,
                validated_data={"title": "x"},
            )

        mock_update.assert_not_called()

    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_raises_value_error_when_update_returns_none(
        self, mock_get_by_id, mock_update
    ):
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        mock_update.return_value = None

        with self.assertRaises(ValueError) as ctx:
            PostService.update_post_by_id(
                post_id=str(model.id),
                user_id=self.user_id,
                validated_data={"title": "x"},
            )

        self.assertIn(str(model.id), str(ctx.exception))


class UpdatePostCloseOutHookTests(TestCase):
    def setUp(self):
        self.user_id = "owner-id"

    @patch("backend.services.post_service.SpaceParticipantRepository.close_out")
    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_transition_to_ended_closes_out_participants_at_ended_at(
        self, mock_get_by_id, mock_update, mock_close_out
    ):
        ended_at = datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        mock_update.return_value = build_post_model(
            created_by=self.user_id,
            status=PostModel.SpaceStatus.ENDED,
            ended_at=ended_at,
        )

        PostService.update_post_by_id(
            post_id=str(model.id),
            user_id=self.user_id,
            validated_data={"status": SpaceStatus.ENDED.value},
        )

        mock_close_out.assert_called_once_with(post_id=str(model.id), ended_at=ended_at)

    @patch("backend.services.post_service.SpaceParticipantRepository.close_out")
    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_transition_to_closed_closes_out_participants(
        self, mock_get_by_id, mock_update, mock_close_out
    ):
        ended_at = datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc)
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        mock_update.return_value = build_post_model(
            created_by=self.user_id,
            status=PostModel.SpaceStatus.CLOSED,
            ended_at=ended_at,
        )

        PostService.update_post_by_id(
            post_id=str(model.id),
            user_id=self.user_id,
            validated_data={"status": SpaceStatus.CLOSED.value},
        )

        mock_close_out.assert_called_once_with(post_id=str(model.id), ended_at=ended_at)

    @patch("backend.services.post_service.SpaceParticipantRepository.close_out")
    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_non_terminal_update_does_not_close_out(
        self, mock_get_by_id, mock_update, mock_close_out
    ):
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        mock_update.return_value = build_post_model(
            created_by=self.user_id,
            status=PostModel.SpaceStatus.LIVE,
        )

        PostService.update_post_by_id(
            post_id=str(model.id),
            user_id=self.user_id,
            validated_data={"status": SpaceStatus.LIVE.value},
        )

        mock_close_out.assert_not_called()

    @patch("backend.services.post_service.SpaceParticipantRepository.close_out")
    @patch("backend.services.post_service.PostRepository.update_by_id")
    @patch("backend.services.post_service.PostRepository.get_by_id")
    def test_close_out_uses_now_when_ended_at_missing(
        self, mock_get_by_id, mock_update, mock_close_out
    ):
        model = build_post_model(created_by=self.user_id)
        mock_get_by_id.return_value = model
        mock_update.return_value = build_post_model(
            created_by=self.user_id,
            status=PostModel.SpaceStatus.ENDED,
            ended_at=None,
        )

        PostService.update_post_by_id(
            post_id=str(model.id),
            user_id=self.user_id,
            validated_data={"status": SpaceStatus.ENDED.value},
        )

        mock_close_out.assert_called_once()
        _, kwargs = mock_close_out.call_args
        self.assertEqual(kwargs["post_id"], str(model.id))
        self.assertIsInstance(kwargs["ended_at"], datetime)


# Exercise the non-detailed error branch to cover the `else` of the error builder.
@override_settings(ERROR_DETAILS=False, DEBUG=False)
class CreatePostErrorWithoutDetailsTests(TestCase):
    @patch("backend.services.post_service.PostRepository.create")
    def test_repository_error_uses_string_errors(self, mock_create):
        mock_create.side_effect = ValueError("db exploded")
        dto = CreatePostDTO(title="x", created_by="user")

        with self.assertRaises(ValueError) as ctx:
            PostService.create_post(dto)

        error = ctx.exception.args[0]
        self.assertIsInstance(error, ApiErrorResponse)
        self.assertEqual(error.errors, ApiErrors.UNEXPECTED_ERROR_OCCURRED)
