from pydantic import BaseModel
from backend.dto.reminder_dto import ReminderDTO


class GetReminderBySpaceIdResponse(BaseModel):
    data: ReminderDTO
