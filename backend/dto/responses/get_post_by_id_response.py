from pydantic import BaseModel
from backend.dto.post_dto import PostDTO


class GetPostByIdResponse(BaseModel):
    data: PostDTO
    token: str | None
