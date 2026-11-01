from pydantic import BaseModel


class LikeStateDTO(BaseModel):
    liked: bool
    likeCount: int
