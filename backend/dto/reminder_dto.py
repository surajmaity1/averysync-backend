import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateUpdateReminderDTO(BaseModel):
    space_id: uuid.UUID
    isReminderSet: bool
    created_by: str


class ReminderDTO(BaseModel):
    id: uuid.UUID
    isReminderSet: bool
    spaceId: uuid.UUID
    createdAt: datetime
    createdBy: str
    updatedAt: datetime | None = None
