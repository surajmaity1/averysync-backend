import json
import uuid
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from rest_framework import status

from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    CannotMessageSelfException,
    ConversationNotFoundException,
    ConversationRequestNotFoundException,
    NotConversationMemberException,
)
from backend.views.conversation import (
    ConversationAcceptView,
    ConversationDeclineView,
    ConversationDetailView,
    ConversationReadView,
    ConversationsView,
    ConversationUnreadCountView,
)

SERVICE = "backend.views.conversation.ConversationService"


def _dto():
    dto = MagicMock()
    dto.model_dump.return_value = {"id": str(uuid.uuid4()), "state": "ACCEPTED"}
    return dto


def _list_response():
    response = MagicMock()
    response.model_dump.return_value = {
        "data": [],
        "nextCursor": None,
        "hasMore": False,
    }
    return response


class CreateConversationViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.participant_id = str(uuid.uuid4())

    def _post(self, body):
        request = self.factory.post(
            "/v1/conversations",
            data=json.dumps(body),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return ConversationsView.as_view()(request)

    @patch(f"{SERVICE}.create_or_get_direct")
    def test_create_new_returns_201(self, mocked):
        mocked.return_value = (_dto(), True)
        response = self._post({"participantId": self.participant_id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{SERVICE}.create_or_get_direct")
    def test_existing_returns_200(self, mocked):
        mocked.return_value = (_dto(), False)
        response = self._post({"participantId": self.participant_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_missing_participant_returns_400(self):
        response = self._post({})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.create_or_get_direct")
    def test_self_dm_returns_400(self, mocked):
        mocked.side_effect = CannotMessageSelfException()
        response = self._post({"participantId": self.participant_id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.create_or_get_direct")
    def test_blocked_returns_404(self, mocked):
        mocked.side_effect = CannotMessageBlockedUserException(self.participant_id)
        response = self._post({"participantId": self.participant_id})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(f"{SERVICE}.create_or_get_direct")
    def test_unexpected_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._post({"participantId": self.participant_id})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListConversationViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    def _get(self, query=""):
        request = self.factory.get(f"/v1/conversations{query}")
        request.user_id = self.caller_id
        return ConversationsView.as_view()(request)

    @patch(f"{SERVICE}.list")
    def test_list_returns_200(self, mocked):
        mocked.return_value = _list_response()
        response = self._get("?section=primary")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(f"{SERVICE}.list")
    def test_requests_section_returns_200(self, mocked):
        mocked.return_value = _list_response()
        response = self._get("?section=requests")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_section_returns_400(self):
        response = self._get("?section=bogus")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_limit_returns_400(self):
        response = self._get("?limit=0")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ConversationDetailViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

    def _get(self, conversation_id):
        request = self.factory.get(f"/v1/conversations/{conversation_id}")
        request.user_id = self.caller_id
        return ConversationDetailView.as_view()(
            request, conversation_id=conversation_id
        )

    @patch(f"{SERVICE}.detail")
    def test_detail_returns_200(self, mocked):
        mocked.return_value = _dto()
        # Django's <uuid:> converter passes a UUID object, not a string.
        response = self._get(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_uuid_returns_400(self):
        response = self._get("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.detail")
    def test_non_member_returns_403(self, mocked):
        mocked.side_effect = NotConversationMemberException(str(self.conversation_id))
        response = self._get(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch(f"{SERVICE}.detail")
    def test_missing_returns_404(self, mocked):
        mocked.side_effect = ConversationNotFoundException(str(self.conversation_id))
        response = self._get(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AcceptDeclineViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

    def _accept(self, conversation_id):
        request = self.factory.post(f"/v1/conversations/{conversation_id}/accept")
        request.user_id = self.caller_id
        return ConversationAcceptView.as_view()(
            request, conversation_id=conversation_id
        )

    def _decline(self, conversation_id):
        request = self.factory.post(f"/v1/conversations/{conversation_id}/decline")
        request.user_id = self.caller_id
        return ConversationDeclineView.as_view()(
            request, conversation_id=conversation_id
        )

    @patch(f"{SERVICE}.accept")
    def test_accept_returns_200(self, mocked):
        mocked.return_value = _dto()
        response = self._accept(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(f"{SERVICE}.accept")
    def test_accept_no_request_returns_404(self, mocked):
        mocked.side_effect = ConversationRequestNotFoundException(
            str(self.conversation_id)
        )
        response = self._accept(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept_bad_uuid_returns_400(self):
        response = self._accept("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.decline")
    def test_decline_returns_204(self, mocked):
        mocked.return_value = None
        response = self._decline(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(f"{SERVICE}.decline")
    def test_decline_no_request_returns_404(self, mocked):
        mocked.side_effect = ConversationRequestNotFoundException(
            str(self.conversation_id)
        )
        response = self._decline(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UnreadCountViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    def _get(self):
        request = self.factory.get("/v1/conversations/unread-count")
        request.user_id = self.caller_id
        return ConversationUnreadCountView.as_view()(request)

    @patch(f"{SERVICE}.unread_conversations_count")
    def test_returns_200_with_count(self, mocked):
        mocked.return_value = 7
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 7)

    @patch(f"{SERVICE}.unread_conversations_count")
    def test_unexpected_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkReadViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.conversation_id = uuid.uuid4()

    def _post(self, conversation_id):
        request = self.factory.post(f"/v1/conversations/{conversation_id}/read")
        request.user_id = self.caller_id
        return ConversationReadView.as_view()(request, conversation_id=conversation_id)

    @patch(f"{SERVICE}.mark_read")
    def test_read_returns_204(self, mocked):
        mocked.return_value = None
        response = self._post(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_read_bad_uuid_returns_400(self):
        response = self._post("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.mark_read")
    def test_read_non_member_returns_403(self, mocked):
        mocked.side_effect = NotConversationMemberException(str(self.conversation_id))
        response = self._post(self.conversation_id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
