import uuid
from datetime import datetime

from pydantic import BaseModel


class BlockDTO(BaseModel):
    id: uuid.UUID
    blockerId: uuid.UUID
    blockedId: uuid.UUID
    createdAt: datetime


class BlockUserDTO(BaseModel):
    id: uuid.UUID
    name: str
    image: str | None = None
    blockedAt: datetime | None = None
