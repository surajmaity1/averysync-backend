from datetime import datetime
from pydantic import BaseModel, field_validator
from backend.constants.post import PostType, SpaceStatus
import uuid


class PostDTO(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    type: PostType
    isRecorded: bool | None = None
    scheduledStartedAt: datetime | None = None
    scheduledEndedAt: datetime | None = None
    startedAt: datetime | None = None
    endedAt: datetime | None = None
    createdInTimezone: str | None = None
    status: SpaceStatus | None = None
    createdAt: datetime
    updatedAt: datetime | None = None
    createdBy: str
    updatedBy: str | None = None


class CreatePostDTO(BaseModel):
    title: str
    description: str | None = None
    type: PostType = PostType.POST
    isRecorded: bool | None = None
    created_by: str

    @field_validator("type", mode="before")
    def parse_type(cls, value):
        if isinstance(type, str):
            return PostType[value]
        return value


class UpdatePostDTO(BaseModel):
    title: str | None = None
    description: str | None = None
    isRecorded: bool | None = None
    scheduledStartedAt: datetime | None = None
    scheduledEndedAt: datetime | None = None
    startedAt: datetime | None = None
    endedAt: datetime | None = None
    createdInTimezone: str | None = None
    status: SpaceStatus | None = None

    @field_validator("status", mode="before")
    def parse_status(cls, value):
        if isinstance(value, str):
            return SpaceStatus[value]
        return value
