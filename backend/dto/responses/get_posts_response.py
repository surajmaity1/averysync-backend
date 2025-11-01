from backend.dto.responses.paginated_response import PaginatedResponse
from typing import List
from backend.dto.post_dto import PostDTO


class GetPostsResponse(PaginatedResponse):
    posts: List[PostDTO] = []
