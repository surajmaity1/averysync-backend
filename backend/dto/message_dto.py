import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from backend.constants.chat import MessageType


class MessageDTO(BaseModel):
    id: uuid.UUID
    conversationId: uuid.UUID
    senderId: uuid.UUID
    type: str
    body: str | None = None
    metadata: dict | None = None
    isDeleted: bool = False
    createdAt: datetime

    @field_validator("type", mode="before")
    def parse_type(cls, value):
        if isinstance(value, MessageType):
            return value.name
        if isinstance(value, int):
            return MessageType(value).name
        return value
