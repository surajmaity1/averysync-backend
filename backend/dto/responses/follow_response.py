from pydantic import BaseModel

from backend.dto.follow_dto import FollowDTO


class FollowResponse(BaseModel):
    data: FollowDTO
