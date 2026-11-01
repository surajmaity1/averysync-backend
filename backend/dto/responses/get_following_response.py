from backend.dto.follow_dto import FollowUserDTO
from backend.dto.responses.paginated_response import PaginatedResponse


class GetFollowingResponse(PaginatedResponse):
    data: list[FollowUserDTO]
    total: int
    limit: int
    offset: int
