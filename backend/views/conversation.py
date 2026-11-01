from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.constants.chat import ConversationSection
from backend.constants.messages import ApiErrors, ValidationErrors
from backend.dto.responses.error_response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiErrorSource,
)
from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    CannotMessageSelfException,
    ConversationNotFoundException,
    ConversationRequestNotFoundException,
    NotConversationMemberException,
)
from backend.serializers.create_conversation_serializer import (
    CreateConversationSerializer,
)
from backend.serializers.cursor_pagination_serializer import (
    CursorPaginationSerializer,
)
from backend.services.conversation_service import ConversationService
from backend.utils.cursor import InvalidCursorError
from backend.utils.uuid_validation import validate_uuid


class ChatErrorMixin:
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
        return getattr(exception, "message", None) or str(exception)

    def _handle_domain_exception(self, exception: Exception) -> Response:
        if isinstance(exception, CannotMessageSelfException):
            return self._error(
                status.HTTP_400_BAD_REQUEST, self._message_of(exception), exception
            )
        if isinstance(exception, InvalidCursorError):
            return self._error(
                status.HTTP_400_BAD_REQUEST, ValidationErrors.CURSOR_INVALID, exception
            )
        if isinstance(exception, NotConversationMemberException):
            return self._error(
                status.HTTP_403_FORBIDDEN, self._message_of(exception), exception
            )
        if isinstance(
            exception,
            (
                ConversationNotFoundException,
                ConversationRequestNotFoundException,
                CannotMessageBlockedUserException,
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
        serializer = CursorPaginationSerializer(data=request.query_params)
        if not serializer.is_valid():
            return None, self._validation_error(serializer.errors)
        return serializer.validated_data, None

    def _section(self, request: Request):
        raw = request.query_params.get("section", "primary")
        try:
            return ConversationSection(raw), None
        except ValueError:
            return None, self._validation_error(
                {"section": ValidationErrors.SECTION_INVALID}
            )


class ConversationsView(ChatErrorMixin, APIView):
    def post(self, request: Request):
        serializer = CreateConversationSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)
        try:
            dto, created = ConversationService.create_or_get_direct(
                caller_id=request.user_id,
                participant_id=serializer.validated_data["participantId"],
            )
            return Response(
                data={"data": dto.model_dump(mode="json")},
                status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)

    def get(self, request: Request):
        section, error = self._section(request)
        if error is not None:
            return error
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = ConversationService.list(
                caller_id=request.user_id,
                section=section,
                limit=page["limit"],
                cursor=page.get("cursor"),
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class ConversationUnreadCountView(ChatErrorMixin, APIView):
    def get(self, request: Request):
        try:
            count = ConversationService.unread_conversations_count(request.user_id)
            return Response(data={"data": {"count": count}}, status=status.HTTP_200_OK)
        except Exception as exception:
            return self._handle_domain_exception(exception)


class ConversationReadView(ChatErrorMixin, APIView):
    def post(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        try:
            ConversationService.mark_read(request.user_id, conversation_id)
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)


class ConversationDetailView(ChatErrorMixin, APIView):
    def get(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        try:
            dto = ConversationService.detail(request.user_id, conversation_id)
            return Response(
                data={"data": dto.model_dump(mode="json")}, status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class ConversationAcceptView(ChatErrorMixin, APIView):
    def post(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        try:
            dto = ConversationService.accept(request.user_id, conversation_id)
            return Response(
                data={"data": dto.model_dump(mode="json")}, status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class ConversationDeclineView(ChatErrorMixin, APIView):
    def post(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        try:
            ConversationService.decline(request.user_id, conversation_id)
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)
