from django.test import SimpleTestCase

from backend.constants.messages import ApiErrors
from backend.exceptions.chat_exception import (
    CannotMessageBlockedUserException,
    CannotMessageSelfException,
    ConversationNotFoundException,
    ConversationRequestNotFoundException,
    NotConversationMemberException,
)

CONVERSATION_ID = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"
USER_ID = "28cbefee-136e-4a33-b73e-8533599e5222"


class ChatExceptionTests(SimpleTestCase):
    def test_cannot_message_self_uses_constant_message(self):
        exception = CannotMessageSelfException()

        self.assertEqual(str(exception), ApiErrors.CANNOT_MESSAGE_SELF)

    def test_blocked_user_is_non_disclosing(self):
        exception = CannotMessageBlockedUserException(user_id=USER_ID)

        self.assertEqual(str(exception), ApiErrors.USER_UNAVAILABLE.format(USER_ID))

    def test_conversation_not_found_formats_id(self):
        exception = ConversationNotFoundException(conversation_id=CONVERSATION_ID)

        self.assertEqual(
            str(exception),
            ApiErrors.CONVERSATION_NOT_FOUND_WITH_ID.format(CONVERSATION_ID),
        )

    def test_not_member_formats_id(self):
        exception = NotConversationMemberException(conversation_id=CONVERSATION_ID)

        self.assertEqual(
            str(exception), ApiErrors.NOT_CONVERSATION_MEMBER.format(CONVERSATION_ID)
        )

    def test_request_not_found_formats_id(self):
        exception = ConversationRequestNotFoundException(
            conversation_id=CONVERSATION_ID
        )

        self.assertEqual(
            str(exception), ApiErrors.CHAT_REQUEST_NOT_FOUND.format(CONVERSATION_ID)
        )
