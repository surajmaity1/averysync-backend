from datetime import datetime, timezone
from backend.dto.organization_dto import CreateOrganizationDTO, OrganizationDTO
from backend.dto.responses.create_organization_response import (
    CreateOrganizationResponse,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
)
from backend.models.organization import OrganizationModel
from backend.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    @classmethod
    def _prepare_organization_dto(cls, org_model: OrganizationModel) -> OrganizationDTO:
        return OrganizationDTO(
            id=org_model.id,
            name=org_model.name,
            shortName=org_model.short_name,
            description=org_model.description,
            type=org_model.type,
            createdBy=org_model.created_by,
        )

    @classmethod
    def create_organization(
        cls, dto: CreateOrganizationDTO
    ) -> CreateOrganizationResponse:
        existing = OrganizationRepository.get_by_short_name(dto.shortName)
        if existing:
            raise OrganizationAlreadyExistsException(dto.shortName)

        raw_type = dto.type.value if hasattr(dto.type, "value") else int(dto.type)

        org_model = OrganizationModel(
            name=dto.name,
            short_name=dto.shortName,
            description=dto.description,
            type=raw_type,
            created_at=datetime.now(timezone.utc),
            created_by=dto.created_by,
        )

        created_org = OrganizationRepository.create(org_model)
        org_dto = cls._prepare_organization_dto(created_org)
        return CreateOrganizationResponse(data=org_dto)
