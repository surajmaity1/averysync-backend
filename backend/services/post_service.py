from datetime import datetime, timezone
from backend.dto.post_dto import CreatePostDTO, PostDTO, UpdatePostDTO
from backend.dto.responses.create_post_response import CreatePostResponse
from backend.models.post import PostModel
from backend.repositories.post_repository import PostRepository
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from backend.exceptions.auth_exceptions import ApiErrors
from django.conf import settings
from backend.dto.responses.get_posts_response import GetPostsResponse
from django.core.exceptions import ValidationError
from backend.exceptions.post_exception import PostNotFoundException, PostUpdateForbidden, PostAlreadyDeletedException
from backend.constants.messages import ApiErrors


class PostService:
    @classmethod
    def _prepare_post_dto(cls, post_model: PostModel):
        return PostDTO(
            id=post_model.id,
            title=post_model.title,
            description=post_model.description,
            type=post_model.type,
            isRecorded=post_model.is_recorded,
            scheduledStartedAt=post_model.scheduled_started_at,
            scheduledEndedAt=post_model.scheduled_ended_at,
            startedAt=post_model.started_at,
            endedAt=post_model.ended_at,
            createdInTimezone=post_model.created_in_timezone,
            status=post_model.status,
            createdAt=post_model.created_at,
            updatedAt=post_model.updated_at,
            createdBy=post_model.created_by,
            updatedBy=post_model.updated_by,
        )

    @classmethod
    def create_post(cls, dto: CreatePostDTO) -> CreatePostResponse:
        try:
            post = PostModel(
                title=dto.title,
                description=dto.description,
                type=dto.type.name,
                is_recorded=dto.isRecorded,
                created_at=datetime.now(timezone.utc),
                created_by=dto.created_by,
                status=(PostModel.SpaceStatus.SCHEDULED if dto.type.name == 'SPACE' else None),
            )

            created_post = PostRepository.create(post)
            post_dto = cls._prepare_post_dto(created_post)

            return CreatePostResponse(data=post_dto)
        except ValueError as e:
            if isinstance(e.args[0], ApiErrorResponse):
                raise e
            raise ValueError(
                ApiErrorResponse(
                    statusCode=500,
                    message=ApiErrors.REPOSITORY_ERROR,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: 'post_repository'},
                            title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                            description=(str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                        )
                    ] if settings.ERROR_DETAILS else ApiErrors.UNEXPECTED_ERROR_OCCURRED
                )
            )
        except Exception as exception:
            raise ValueError(
                ApiErrorResponse(
                    statusCode=500,
                    message=ApiErrors.INTERNAL_SERVER_ERROR,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: 'server'},
                            title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                            description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                        )
                    ] if settings.ERROR_DETAILS else ApiErrors.UNEXPECTED_ERROR_OCCURRED
                )
            )

    @classmethod
    def get_posts(cls) -> GetPostsResponse:
        try:
            posts = PostRepository.get_posts()

            if not posts:
                return GetPostsResponse(posts=[])

            posts_dto = [cls._prepare_post_dto(post) for post in posts]
            return GetPostsResponse(posts=posts_dto)
        except ValidationError as e:
            return GetPostsResponse(
                posts=[],
                # links=None,
                # errors={
                #     'code': '400',
                #     'message': str(e) if settings.DEBUG else ApiErrors.VALIDATION_ERROR
                # }
            )
        except Exception as e:
            return GetPostsResponse(
                posts=[],
                # links=None,
                # errors={
                #     'code': '500',
                #     'message': str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR
                # }
            )

    @classmethod
    def get_post_by_id(cls, post_id: str) -> PostDTO:
        try:
            post_model = PostRepository.get_by_id(post_id=post_id)

            if not post_model:
                raise PostNotFoundException(post_id=post_id)

            return cls._prepare_post_dto(post_model=post_model)
        except Exception as exception:
            raise ValueError(f'Post with id {post_id} not found: {str(exception)}')

    @classmethod
    def delete_post_by_id(cls, post_id: str, user_id: str) -> bool:
        post = PostRepository.get_by_id(post_id=post_id)

        if not post:
            raise PostNotFoundException(post_id=post_id)

        if not post.created_by == user_id:
            raise PostUpdateForbidden(post_id=post_id)

        if post.is_deleted:
            raise PostAlreadyDeletedException(post_id=post_id)

        post_deleted = PostRepository.delete_by_id(post_id=post_id)

        if not post_deleted:
            return False

        return True

    @classmethod
    def update_post_by_id(cls, post_id: str, user_id: str, validated_data: dict) -> PostDTO:
        try:
            post = PostService.get_post_by_id(post_id=post_id)

            if not post:
                raise ValueError(f'post not found {post_id}')

            if not post.createdBy == user_id:
                raise PostUpdateForbidden(post_id=post_id)

            updated_post = PostRepository.update_by_id(post_id=post_id, update_data=validated_data)

            if not updated_post:
                raise ValueError(ApiErrors.POST_SPACE_UPDATE_FAILED.format(post_id))

            return cls._prepare_post_dto(updated_post)
        except Exception as exception:
            raise ValueError(f'{ApiErrors.POST_SPACE_UPDATE_FAILED.format(post_id)} with exception: {str(exception)}')
