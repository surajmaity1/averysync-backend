from pydantic import BaseModel

from backend.dto.organization_dto import OrganizationDTO


class GetOrganizationByIdResponse(BaseModel):
    data: OrganizationDTO
