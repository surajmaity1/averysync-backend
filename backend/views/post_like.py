from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.constants.messages import ApiErrors
from backend.dto.responses.error_response import ApiErrorDetail, ApiErrorResponse
from backend.dto.responses.like_response import LikeResponse
from backend.exceptions.post_exception import PostNotFoundException
from backend.services.post_like_service import PostLikeService
from backend.utils.uuid_validation import validate_uuid


class PostLikeView(APIView):
    def _error(self, status_code: int, message: str, exception: Exception) -> Response:
        error_response = ApiErrorResponse(
            statusCode=status_code,
            message=message,
            errors=[
                ApiErrorDetail(
                    title=message,
                    description=str(exception) if settings.DEBUG else message,
                )
            ]
            if settings.ERROR_DETAILS
            else message,
        )
        return Response(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status_code,
        )

    def _handle_exception(self, exception: Exception) -> Response:
        if isinstance(exception, PostNotFoundException):
            return self._error(
                status.HTTP_404_NOT_FOUND,
                getattr(exception, "msg", ApiErrors.POST_NOT_FOUND),
                exception,
            )
        return self._error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ApiErrors.UNEXPECTED_ERROR_OCCURRED,
            exception,
        )

    def post(self, request: Request, post_id: str):
        if not validate_uuid(uuid_string=post_id):
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                ApiErrors.VALIDATION_ERROR,
                ValueError(f"invalid id {post_id}"),
            )
        try:
            dto = PostLikeService.like(user_id=request.user_id, post_id=post_id)
            return Response(
                data=LikeResponse(data=dto).model_dump(mode="json"),
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_exception(exception)

    def delete(self, request: Request, post_id: str):
        if not validate_uuid(uuid_string=post_id):
            return self._error(
                status.HTTP_400_BAD_REQUEST,
                ApiErrors.VALIDATION_ERROR,
                ValueError(f"invalid id {post_id}"),
            )
        try:
            dto = PostLikeService.unlike(user_id=request.user_id, post_id=post_id)
            return Response(
                data=LikeResponse(data=dto).model_dump(mode="json"),
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_exception(exception)
