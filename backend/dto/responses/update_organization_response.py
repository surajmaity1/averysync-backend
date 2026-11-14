from pydantic import BaseModel

from backend.constants.messages import ApplicationMessages
from backend.dto.organization_dto import OrganizationDTO


class UpdateOrganizationResponse(BaseModel):
    message: str = ApplicationMessages.ORGANIZATION_UPDATED
    data: OrganizationDTO
