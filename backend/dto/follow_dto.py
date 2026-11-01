import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from backend.constants.follow import FollowStatus, RelationshipStatus


class FollowDTO(BaseModel):
    id: uuid.UUID
    followerId: uuid.UUID
    followeeId: uuid.UUID
    status: str
    requestedAt: datetime
    respondedAt: datetime | None = None
    createdAt: datetime

    @field_validator("status", mode="before")
    def parse_status(cls, value):
        if isinstance(value, FollowStatus):
            return value.name
        if isinstance(value, int):
            return FollowStatus(value).name
        return value


class FollowUserDTO(BaseModel):
    id: uuid.UUID
    name: str
    image: str | None = None
    followedAt: datetime | None = None


class RelationshipDTO(BaseModel):
    status: str
    followsYou: bool

    @field_validator("status", mode="before")
    def parse_status(cls, value):
        if isinstance(value, RelationshipStatus):
            return value.value
        return value
