from pydantic import BaseModel

from backend.dto.space_participant_dto import ParticipantDTO


class GetParticipantsResponse(BaseModel):
    data: list[ParticipantDTO]
