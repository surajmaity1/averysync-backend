import uuid

from pydantic import BaseModel

from backend.dto.follow_dto import RelationshipDTO


class UpdateProfileDTO(BaseModel):
    isPrivate: bool


class ProfileDTO(BaseModel):
    id: uuid.UUID
    name: str
    image: str | None = None
    isPrivate: bool
    followerCount: int
    followingCount: int
    relationship: RelationshipDTO | None = None
