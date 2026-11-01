from backend.constants.messages import ApiErrors


class CannotMessageSelfException(Exception):
    def __init__(self, message: str = ApiErrors.CANNOT_MESSAGE_SELF):
        self.message = message
        super().__init__(self.message)


class CannotMessageBlockedUserException(Exception):
    """Non-disclosing: surfaces as 404 so a block is never revealed."""

    def __init__(self, user_id: str, message: str = ApiErrors.USER_UNAVAILABLE):
        self.message = message.format(user_id)
        super().__init__(self.message)


class ConversationNotFoundException(Exception):
    def __init__(
        self,
        conversation_id: str,
        message: str = ApiErrors.CONVERSATION_NOT_FOUND_WITH_ID,
    ):
        self.message = message.format(conversation_id)
        super().__init__(self.message)


class NotConversationMemberException(Exception):
    def __init__(
        self,
        conversation_id: str,
        message: str = ApiErrors.NOT_CONVERSATION_MEMBER,
    ):
        self.message = message.format(conversation_id)
        super().__init__(self.message)


class ConversationRequestNotFoundException(Exception):
    def __init__(
        self,
        conversation_id: str,
        message: str = ApiErrors.CHAT_REQUEST_NOT_FOUND,
    ):
        self.message = message.format(conversation_id)
        super().__init__(self.message)
