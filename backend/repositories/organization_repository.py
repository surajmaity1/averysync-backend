import logging
from typing import Optional
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
    def get_by_short_name(cls, short_name: str) -> Optional[OrganizationModel]:
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
    def get_by_id(cls, org_id: str) -> Optional[OrganizationModel]:
        try:
            return OrganizationModel.objects.filter(id=org_id, is_deleted=False).first()
        except Exception as exception:
            logger.error(f"Failed to fetch organization: {str(exception)}")
            raise ValueError(
                RepositoryError.ORGANIZATION_FETCH_FAILED.format(str(exception))
            )
