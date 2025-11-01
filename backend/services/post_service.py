from datetime import datetime, timezone
from backend.dto.post_dto import CreatePostDTO, PostDTO
from backend.dto.responses.create_post_response import CreatePostResponse
from backend.models.post import PostModel
from backend.repositories.post_repository import PostRepository
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from backend.exceptions.auth_exceptions import ApiErrors
from django.conf import settings
from backend.dto.responses.get_posts_response import GetPostsResponse
from django.core.exceptions import ValidationError


class PostService:
    @classmethod
    def _prepare_post_dto(cls, post_model: PostModel):
        return PostDTO(
            id=post_model.id,
            title=post_model.title,
            description=post_model.description,
            type=post_model.type,
            isRecorded=post_model.is_recorded,
            createdAt=post_model.created_at,
            updatedAt=post_model.updated_at,
            createdBy= post_model.created_by,
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
                    ]
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
                    ]
                )
            )


    @classmethod
    def get_posts(cls) -> GetPostsResponse:
        try:
            posts = PostRepository.get_posts()
            
            if not posts:
                return GetPostsResponse(posts=[], links=None)
            
            posts_dto = [cls._prepare_post_dto(post) for post in posts]
            return GetPostsResponse(posts=posts_dto)
        except ValidationError as e:
            return GetPostsResponse(
                posts=[],
                links=None,
                errors={
                    'code': '400',
                    'message': str(e) if settings.DEBUG else ApiErrors.VALIDATION_ERROR
                }
            )
        except Exception as e:
            return GetPostsResponse(
                posts=[],
                links=None,
                errors={
                    'code': '500',
                    'message': str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR
                }
            )
