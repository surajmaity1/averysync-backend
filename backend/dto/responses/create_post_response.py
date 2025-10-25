from pydantic import BaseModel

from backend.constants.messages import ApplicationMessages
from backend.dto.post_dto import PostDTO


class CreatePostResponse(BaseModel):
    statusCode: int = 201
    message: str = ApplicationMessages.POST_CREATED
    data: PostDTO
