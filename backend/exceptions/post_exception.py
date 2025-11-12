from backend.constants.messages import ApiErrors

class PostNotFoundException(Exception):
    def __init__(self, post_id: str | None = None, msg: str = ApiErrors.POST_NOT_FOUND_WITH_ID):
        if post_id:
            self.msg = msg.format(post_id)
        else:
            self.msg = ApiErrors.POST_NOT_FOUND
        super().__init__(self.msg)