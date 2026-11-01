import json
import uuid
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from rest_framework import status

from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    ConversationNotFoundException,
    NotConversationMemberException,
)
from backend.views.message import MessagesView

SERVICE = "backend.views.message.MessageService"


def _message_dto():
    dto = MagicMock()
    dto.model_dump.return_value = {"id": str(uuid.uuid4()), "body": "hey"}
    return dto


def _list_response():
    response = MagicMock()
    response.model_dump.return_value = {
        "data": [],
        "nextCursor": None,
        "hasMore": False,
    }
    return response


class SendMessageViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

    def _post(self, conversation_id, body):
        request = self.factory.post(
            f"/v1/conversations/{conversation_id}/messages",
            data=json.dumps(body),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return MessagesView.as_view()(request, conversation_id=conversation_id)

    @patch(f"{SERVICE}.send")
    def test_send_returns_201(self, mocked):
        mocked.return_value = _message_dto()
        response = self._post(self.conversation_id, {"body": "hey there"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bad_uuid_returns_400(self):
        response = self._post("not-a-uuid", {"body": "hey"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_blank_body_returns_400(self):
        response = self._post(self.conversation_id, {"body": "   "})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.send")
    def test_non_member_returns_403(self, mocked):
        mocked.side_effect = NotConversationMemberException(str(self.conversation_id))
        response = self._post(self.conversation_id, {"body": "hey"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(f"{SERVICE}.send")
    def test_blocked_returns_404(self, mocked):
        mocked.side_effect = CannotMessageBlockedUserException(str(uuid.uuid4()))
        response = self._post(self.conversation_id, {"body": "hey"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.send")
    def test_missing_conversation_returns_404(self, mocked):
        mocked.side_effect = ConversationNotFoundException(str(self.conversation_id))
        response = self._post(self.conversation_id, {"body": "hey"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.send")
    def test_unexpected_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._post(self.conversation_id, {"body": "hey"})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageHistoryViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

    def _get(self, conversation_id, query=""):
        request = self.factory.get(
            f"/v1/conversations/{conversation_id}/messages{query}"
        )
        request.user_id = self.caller_id
        return MessagesView.as_view()(request, conversation_id=conversation_id)

    @patch(f"{SERVICE}.list_messages")
    def test_history_returns_200(self, mocked):
        mocked.return_value = _list_response()
        response = self._get(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_history_bad_uuid_returns_400(self):
        response = self._get("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.list_messages")
    def test_history_non_member_returns_403(self, mocked):
        mocked.side_effect = NotConversationMemberException(str(self.conversation_id))
        response = self._get(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
