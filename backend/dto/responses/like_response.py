from pydantic import BaseModel

from backend.dto.post_like_dto import LikeStateDTO


class LikeResponse(BaseModel):
    data: LikeStateDTO
