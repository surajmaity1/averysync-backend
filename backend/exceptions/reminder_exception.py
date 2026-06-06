from backend.constants.messages import ApiErrors


class ReminderNotFoundException(Exception):
    def __init__(
        self,
        space_id: str | None = None,
        msg: str = ApiErrors.REMINDER_NOT_FOUND_WITH_ID,
    ):
        if space_id:
            self.msg = msg.format(space_id)
        else:
            self.msg = ApiErrors.REMINDER_NOT_FOUND
        super().__init__(self.msg)
