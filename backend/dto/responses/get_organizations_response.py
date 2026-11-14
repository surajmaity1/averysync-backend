from pydantic import BaseModel

from backend.dto.organization_dto import OrganizationDTO


class GetOrganizationsResponse(BaseModel):
    data: list[OrganizationDTO] = []
