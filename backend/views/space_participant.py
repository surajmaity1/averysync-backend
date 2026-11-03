from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from backend.constants.messages import ApiErrors
from backend.dto.responses.error_response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiErrorSource,
)
from backend.dto.space_participant_dto import MuteParticipantDTO
from backend.exceptions.participant_exception import (
    ModerationForbiddenException,
    ParticipantNotFoundException,
    SelfMuteNotAllowedException,
    SpaceEndedException,
    SpaceNotLiveException,
)
from backend.exceptions.post_exception import SpaceNotFoundException
from backend.serializers.mute_participant_serializer import MuteParticipantSerializer
from backend.services.space_participant_service import SpaceParticipantService
from backend.utils.uuid_validation import validate_uuid


class _ParticipantErrorMixin:
    def _validation_error(self, errors) -> Response:
        formatted_errors = []
        for fields, messages in errors.items():
            formatted_errors.append(
                ApiErrorDetail(
                    source={ApiErrorSource.PARAMETER: fields},
                    title=ApiErrors.VALIDATION_ERROR,
                    description=str(messages),
                )
            )
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=ApiErrors.VALIDATION_ERROR,
            errors=formatted_errors,
        )
        return Response(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_400_BAD_REQUEST,
        )

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

    def _handle_domain_exception(self, exception: Exception, space_id: str) -> Response:
        if isinstance(exception, SelfMuteNotAllowedException):
            return self._error(
                status.HTTP_400_BAD_REQUEST, exception.message, exception
            )
        if isinstance(exception, ModerationForbiddenException):
            return self._error(status.HTTP_403_FORBIDDEN, exception.message, exception)
        if isinstance(
            exception, (ParticipantNotFoundException, SpaceNotFoundException)
        ):
            message = getattr(
                exception, "message", ApiErrors.POST_NOT_FOUND_WITH_ID.format(space_id)
            )
            return self._error(status.HTTP_404_NOT_FOUND, message, exception)
        if isinstance(exception, SpaceNotLiveException):
            return self._error(status.HTTP_409_CONFLICT, exception.message, exception)
        if isinstance(exception, SpaceEndedException):
            return self._error(status.HTTP_410_GONE, exception.message, exception)
        return self._error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ApiErrors.UNEXPECTED_ERROR_OCCURRED,
            exception,
        )

    def _bad_uuid(self, value: str) -> Response:
        message = ApiErrors.VALIDATION_ERROR
        return self._error(
            status.HTTP_400_BAD_REQUEST, message, ValueError(f"invalid id {value}")
        )


class ParticipantsView(_ParticipantErrorMixin, APIView):
    def post(self, request: Request, space_id: str):
        if not validate_uuid(uuid_string=space_id):
            return self._bad_uuid(space_id)
        try:
            response, created = SpaceParticipantService.join(
                space_id=space_id, user_id=request.user_id
            )
            return Response(
                data=response.model_dump(mode="json"),
                status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
            )
        except Exception as exception:
            return self._handle_domain_exception(exception, space_id)

    def get(self, request: Request, space_id: str):
        if not validate_uuid(uuid_string=space_id):
            return self._bad_uuid(space_id)
        try:
            include_left = request.query_params.get("includeLeft", "").lower() == "true"
            response = SpaceParticipantService.get_participants(
                space_id=space_id, include_left=include_left
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception, space_id)


class ParticipantDetailView(_ParticipantErrorMixin, APIView):
    def delete(self, request: Request, space_id: str, user_id: str):
        if not validate_uuid(uuid_string=space_id):
            return self._bad_uuid(space_id)
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            SpaceParticipantService.leave_or_remove(
                space_id=space_id,
                target_user_id=user_id,
                caller_id=request.user_id,
            )
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception, space_id)


class ParticipantMuteView(_ParticipantErrorMixin, APIView):
    def patch(self, request: Request, space_id: str, user_id: str):
        if not validate_uuid(uuid_string=space_id):
            return self._bad_uuid(space_id)
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)

        serializer = MuteParticipantSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        try:
            dto = MuteParticipantDTO(**serializer.validated_data)
            participant = SpaceParticipantService.set_mute_state(
                space_id=space_id,
                target_user_id=user_id,
                caller_id=request.user_id,
                dto=dto,
            )
            return Response(
                data={"data": participant.model_dump(mode="json")},
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception, space_id)
