from datetime import datetime
from pydantic import BaseModel, field_validator
from backend.constants.post import PostType
from backend.dto.user_dto import UserDTO
import uuid


class PostDTO(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    type: PostType
    isRecorded: bool | None = None
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


    @field_validator('type', mode='before')
    def parse_type(cls, value):
        if isinstance(type, str):
            return PostType[value]
        return value
