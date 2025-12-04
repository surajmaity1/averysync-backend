from pydantic import BaseModel

from backend.constants.messages import ApplicationMessages
from backend.dto.post_dto import PostDTO


class CreatePostResponse(BaseModel):
    message: str = ApplicationMessages.POST_CREATED
    data: PostDTO
