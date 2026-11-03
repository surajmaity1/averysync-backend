from backend.dto.block_dto import BlockUserDTO
from backend.dto.responses.paginated_response import PaginatedResponse


class GetBlocksResponse(PaginatedResponse):
    data: list[BlockUserDTO]
    total: int
    limit: int
    offset: int
