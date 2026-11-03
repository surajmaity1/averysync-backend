from backend.constants.messages import ApiErrors


class ParticipantNotFoundException(Exception):
    def __init__(
        self,
        user_id: str,
        space_id: str,
        message: str = ApiErrors.PARTICIPANT_NOT_FOUND_WITH_ID,
    ):
        self.message = message.format(user_id, space_id)
        super().__init__(self.message)


class ModerationForbiddenException(Exception):
    def __init__(self, space_id: str, message: str = ApiErrors.MODERATION_NOT_ALLOWED):
        self.message = message.format(space_id)
        super().__init__(self.message)


class SpaceNotLiveException(Exception):
    def __init__(self, space_id: str, message: str = ApiErrors.SPACE_NOT_LIVE):
        self.message = message.format(space_id)
        super().__init__(self.message)


class SpaceEndedException(Exception):
    def __init__(self, space_id: str, message: str = ApiErrors.SPACE_ALREADY_ENDED):
        self.message = message.format(space_id)
        super().__init__(self.message)


class SelfMuteNotAllowedException(Exception):
    def __init__(self, message: str = ApiErrors.SELF_MUTE_NOT_ALLOWED):
        self.message = message
        super().__init__(self.message)
