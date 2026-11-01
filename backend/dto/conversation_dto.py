import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from backend.constants.chat import ConversationType, MemberState


class ConversationPeerDTO(BaseModel):
    id: uuid.UUID
    name: str
    image: str | None = None


class ConversationSummaryDTO(BaseModel):
    id: uuid.UUID
    type: str
    # The other participant for a DIRECT conversation (None for groups in v1).
    peer: ConversationPeerDTO | None = None
    title: str | None = None
    # The caller's own membership state — PENDING marks a message request.
    state: str
    lastMessagePreview: str | None = None
    lastMessageAt: datetime | None = None
    unreadCount: int = 0

    @field_validator("type", mode="before")
    def parse_type(cls, value):
        if isinstance(value, ConversationType):
            return value.name
        if isinstance(value, int):
            return ConversationType(value).name
        return value

    @field_validator("state", mode="before")
    def parse_state(cls, value):
        if isinstance(value, MemberState):
            return value.name
        if isinstance(value, int):
            return MemberState(value).name
        return value


class ConversationDetailDTO(ConversationSummaryDTO):
    pass
