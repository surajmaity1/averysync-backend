import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from backend.constants.participant import ParticipantRole


class ParticipantDTO(BaseModel):
    id: uuid.UUID
    spaceId: uuid.UUID
    userId: uuid.UUID
    role: str
    isMuted: bool
    mutedUntil: datetime | None = None
    firstJoinedAt: datetime
    lastJoinedAt: datetime
    leftAt: datetime | None = None

    @field_validator("role", mode="before")
    def parse_role(cls, value):
        if isinstance(value, int):
            return ParticipantRole(value).name
        if isinstance(value, ParticipantRole):
            return value.name
        return value


class MuteParticipantDTO(BaseModel):
    isMuted: bool
    durationSeconds: int | None = None
    reason: str | None = None
