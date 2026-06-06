from backend.constants.messages import ApiErrors


class PostNotFoundException(Exception):
    def __init__(
        self, post_id: str | None = None, msg: str = ApiErrors.POST_NOT_FOUND_WITH_ID
    ):
        if post_id:
            self.msg = msg.format(post_id)
        else:
            self.msg = ApiErrors.POST_NOT_FOUND
        super().__init__(self.msg)


class PostUpdateForbidden(Exception):
    def __init__(
        self, post_id: str, message: str = ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED
    ):
        self.message = message.format(post_id)
        super().__init__(self.message)


class PostAlreadyDeletedException(Exception):
    def __init__(self, post_id: str, message: str = ApiErrors.POST_ALREADY_DELETED):
        self.message = message.format(post_id)
        super().__init__(self.message)


class SpaceNotFoundException(Exception):
    def __init__(self, space_id: str, message: str = ApiErrors.SPACE_NOT_FOUND):
        self.message = message.format(space_id)
        super().__init__(self.message)
