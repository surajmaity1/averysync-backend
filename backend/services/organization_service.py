from datetime import datetime, timezone
from backend.dto.organization_dto import (
    CreateOrganizationDTO,
    OrganizationDTO,
    UpdateOrganizationDTO,
)
from backend.dto.responses.create_organization_response import (
    CreateOrganizationResponse,
)
from backend.dto.responses.get_organizations_response import (
    GetOrganizationsResponse,
)
from backend.dto.responses.update_organization_response import (
    UpdateOrganizationResponse,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateForbiddenException,
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

    @classmethod
    def get_all_organizations(cls) -> GetOrganizationsResponse:
        organizations = OrganizationRepository.get_all()
        return GetOrganizationsResponse(
            data=[cls._prepare_organization_dto(org) for org in organizations]
        )

    @classmethod
    def update_organization(
        cls, org_id: str, user_id: str, dto: UpdateOrganizationDTO
    ) -> UpdateOrganizationResponse:
        org = OrganizationRepository.get_by_id(org_id)
        if not org or org.is_deleted:
            raise OrganizationNotFoundException(org_id)

        if str(org.created_by) != str(user_id):
            raise OrganizationUpdateForbiddenException(org_id)

        if dto.shortName is not None and dto.shortName != org.short_name:
            existing = OrganizationRepository.get_by_short_name(dto.shortName)
            if existing and str(existing.id) != str(org_id):
                raise OrganizationAlreadyExistsException(dto.shortName)

        update_data = {}
        if dto.name is not None:
            update_data["name"] = dto.name
        if dto.shortName is not None:
            update_data["short_name"] = dto.shortName
        if dto.description is not None:
            update_data["description"] = dto.description
        if dto.type is not None:
            raw_type = dto.type.value if hasattr(dto.type, "value") else int(dto.type)
            update_data["type"] = raw_type

        updated_org = OrganizationRepository.update(
            org_id=org_id,
            update_data=update_data,
            updated_by=str(user_id),
        )
        if not updated_org:
            raise OrganizationNotFoundException(org_id)

        org_dto = cls._prepare_organization_dto(updated_org)
        return UpdateOrganizationResponse(data=org_dto)
