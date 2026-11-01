from pydantic import BaseModel

from backend.dto.profile_dto import ProfileDTO


class ProfileResponse(BaseModel):
    data: ProfileDTO
