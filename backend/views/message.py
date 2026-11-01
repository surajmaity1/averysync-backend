from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.serializers.send_message_serializer import SendMessageSerializer
from backend.services.message_service import MessageService
from backend.utils.uuid_validation import validate_uuid
from backend.views.conversation import ChatErrorMixin


class MessagesView(ChatErrorMixin, APIView):
    def post(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)
        try:
            dto = MessageService.send(
                caller_id=request.user_id,
                conversation_id=conversation_id,
                body=serializer.validated_data["body"],
                client_message_id=serializer.validated_data.get("clientMessageId"),
            )
            return Response(
                data={"data": dto.model_dump(mode="json")},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)

    def get(self, request: Request, conversation_id):
        if not validate_uuid(uuid_string=conversation_id):
            return self._bad_uuid(conversation_id)
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = MessageService.list_messages(
                caller_id=request.user_id,
                conversation_id=conversation_id,
                limit=page["limit"],
                cursor=page.get("cursor"),
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)
