from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.constants.messages import ApiErrors
from backend.dto.responses.error_response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiErrorSource,
)
from backend.dto.responses.follow_response import FollowResponse
from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import (
    CannotBlockSelfException,
    CannotFollowSelfException,
    FollowerNotFoundException,
    FollowForbiddenException,
    FollowRequestNotFoundException,
    NotFollowingException,
    UserBlockedException,
)
from backend.serializers.pagination_serializer import PaginationSerializer
from backend.services.follow_service import FollowService
from backend.utils.uuid_validation import validate_uuid


class FollowErrorMixin:
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

    def _validation_error(self, errors) -> Response:
        formatted_errors = [
            ApiErrorDetail(
                source={ApiErrorSource.PARAMETER: field},
                title=ApiErrors.VALIDATION_ERROR,
                description=str(messages),
            )
            for field, messages in errors.items()
        ]
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=ApiErrors.VALIDATION_ERROR,
            errors=formatted_errors,
        )
        return Response(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _bad_uuid(self, value: str) -> Response:
        return self._error(
            status.HTTP_400_BAD_REQUEST,
            ApiErrors.VALIDATION_ERROR,
            ValueError(f"invalid id {value}"),
        )

    def _message_of(self, exception: Exception) -> str:
        return (
            getattr(exception, "message", None)
            or getattr(exception, "msg", None)
            or str(exception)
        )

    def _handle_domain_exception(self, exception: Exception) -> Response:
        if isinstance(exception, (CannotFollowSelfException, CannotBlockSelfException)):
            return self._error(
                status.HTTP_400_BAD_REQUEST, self._message_of(exception), exception
            )
        if isinstance(exception, FollowForbiddenException):
            return self._error(
                status.HTTP_403_FORBIDDEN, self._message_of(exception), exception
            )
        if isinstance(
            exception,
            (
                FollowRequestNotFoundException,
                FollowerNotFoundException,
                NotFollowingException,
                UserBlockedException,
                UserNotFoundException,
            ),
        ):
            return self._error(
                status.HTTP_404_NOT_FOUND, self._message_of(exception), exception
            )
        return self._error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ApiErrors.UNEXPECTED_ERROR_OCCURRED,
            exception,
        )

    def _paginate(self, request: Request):
        serializer = PaginationSerializer(data=request.query_params)
        if not serializer.is_valid():
            return None, self._validation_error(serializer.errors)
        return serializer.validated_data, None


class FollowView(FollowErrorMixin, APIView):
    def post(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            dto, created = FollowService.follow(
                follower_id=request.user_id, target_user_id=user_id
            )
            return Response(
                data=FollowResponse(data=dto).model_dump(mode="json"),
                status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)

    def delete(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            FollowService.unfollow_or_cancel(
                follower_id=request.user_id, target_user_id=user_id
            )
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)


class FollowersView(FollowErrorMixin, APIView):
    def get(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = FollowService.get_followers(
                viewer_id=request.user_id,
                target_user_id=user_id,
                limit=page["limit"],
                offset=page["offset"],
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class FollowingView(FollowErrorMixin, APIView):
    def get(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = FollowService.get_following(
                viewer_id=request.user_id,
                target_user_id=user_id,
                limit=page["limit"],
                offset=page["offset"],
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class FollowRequestsView(FollowErrorMixin, APIView):
    def get(self, request: Request):
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = FollowService.get_requests(
                user_id=request.user_id,
                limit=page["limit"],
                offset=page["offset"],
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class FollowRequestActionView(FollowErrorMixin, APIView):
    def post(self, request: Request, follower_id: str, action: str):
        if not validate_uuid(uuid_string=follower_id):
            return self._bad_uuid(follower_id)
        try:
            if action == "accept":
                dto = FollowService.accept(
                    followee_id=request.user_id, follower_id=follower_id
                )
                return Response(
                    data=FollowResponse(data=dto).model_dump(mode="json"),
                    status=status.HTTP_200_OK,
                )
            FollowService.reject(followee_id=request.user_id, follower_id=follower_id)
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)


class FollowerRemoveView(FollowErrorMixin, APIView):
    def delete(self, request: Request, follower_id: str):
        if not validate_uuid(uuid_string=follower_id):
            return self._bad_uuid(follower_id)
        try:
            FollowService.remove_follower(
                followee_id=request.user_id, follower_id=follower_id
            )
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)
