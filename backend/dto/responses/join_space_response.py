from pydantic import BaseModel

from backend.dto.space_participant_dto import ParticipantDTO


class JoinSpaceResponse(BaseModel):
    data: ParticipantDTO
    token: str | None
