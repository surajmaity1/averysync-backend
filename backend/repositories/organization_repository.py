import logging
from django.db import transaction

from backend.constants.messages import RepositoryError
from backend.models.organization import OrganizationModel

logger = logging.getLogger(__name__)


class OrganizationRepository:
    @classmethod
    @transaction.atomic
    def create(cls, organization: OrganizationModel) -> OrganizationModel:
        try:
            created_org = OrganizationModel.objects.create(
                name=organization.name,
                short_name=organization.short_name,
                description=organization.description,
                type=organization.type,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
                created_by=organization.created_by,
                updated_by=organization.updated_by,
                is_deleted=organization.is_deleted,
            )
            return created_org
        except Exception as exception:
            logger.error(f"Failed to create organization: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_CREATION_FAILED.format(str(exception))
            )

    @classmethod
    def get_by_short_name(cls, short_name: str) -> OrganizationModel | None:
        try:
            return OrganizationModel.objects.filter(
                short_name=short_name, is_deleted=False
            ).first()
        except Exception as exception:
            logger.error(f"Failed to fetch organization: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    def get_by_id(cls, org_id: str) -> OrganizationModel | None:
        try:
            return OrganizationModel.objects.filter(id=org_id, is_deleted=False).first()
        except Exception as exception:
            logger.error(f"Failed to fetch organization: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    def get_all(cls) -> list[OrganizationModel]:
        try:
            return list(
                OrganizationModel.objects.filter(is_deleted=False).order_by(
                    "created_at"
                )
            )
        except Exception as exception:
            logger.error(f"Failed to fetch organizations: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_FETCH_FAILED.format(str(exception))
            )

    @classmethod
    @transaction.atomic
    def update(
        cls,
        org_id: str,
        update_data: dict,
        updated_by: str | None = None,
    ) -> OrganizationModel | None:
        try:
            org = (
                OrganizationModel.objects.select_for_update()
                .filter(id=org_id, is_deleted=False)
                .first()
            )
            if not org:
                return None

            for field, value in update_data.items():
                if hasattr(org, field):
                    setattr(org, field, value)

            if updated_by:
                org.updated_by = updated_by

            org.save()
            return org
        except Exception as exception:
            logger.error(f"Failed to update organization: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_UPDATE_FAILED.format(str(exception))
            )
