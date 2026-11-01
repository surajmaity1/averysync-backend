from backend.constants.messages import ApiErrors


class CannotFollowSelfException(Exception):
    def __init__(self, message: str = ApiErrors.CANNOT_FOLLOW_SELF):
        self.message = message
        super().__init__(self.message)


class CannotBlockSelfException(Exception):
    def __init__(self, message: str = ApiErrors.CANNOT_BLOCK_SELF):
        self.message = message
        super().__init__(self.message)


class FollowForbiddenException(Exception):
    def __init__(
        self,
        user_id: str | None = None,
        message: str = ApiErrors.FOLLOW_LIST_FORBIDDEN,
    ):
        self.user_id = user_id
        self.message = message
        super().__init__(self.message)


class FollowRequestNotFoundException(Exception):
    def __init__(
        self,
        follower_id: str,
        message: str = ApiErrors.FOLLOW_REQUEST_NOT_FOUND,
    ):
        self.message = message.format(follower_id)
        super().__init__(self.message)


class NotFollowingException(Exception):
    def __init__(self, user_id: str, message: str = ApiErrors.NOT_FOLLOWING):
        self.message = message.format(user_id)
        super().__init__(self.message)


class FollowerNotFoundException(Exception):
    def __init__(self, follower_id: str, message: str = ApiErrors.FOLLOWER_NOT_FOUND):
        self.message = message.format(follower_id)
        super().__init__(self.message)


class UserBlockedException(Exception):
    def __init__(self, user_id: str, message: str = ApiErrors.USER_BLOCKED):
        self.message = message.format(user_id)
        super().__init__(self.message)
