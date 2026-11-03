from backend.dto.conversation_dto import ConversationSummaryDTO
from backend.dto.message_dto import MessageDTO
from backend.dto.responses.paginated_response import PaginatedResponse


class ConversationListResponse(PaginatedResponse):
    data: list[ConversationSummaryDTO]
    nextCursor: str | None = None
    hasMore: bool = False


class MessageListResponse(PaginatedResponse):
    data: list[MessageDTO]
    nextCursor: str | None = None
    hasMore: bool = False
