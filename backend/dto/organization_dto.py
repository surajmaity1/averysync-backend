import uuid
from pydantic import BaseModel, ConfigDict, field_validator

from backend.constants.organization import OrganizationType


def parse_organization_type(value: int | str | OrganizationType) -> OrganizationType:
    if isinstance(value, OrganizationType):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return OrganizationType(value)
    if isinstance(value, str):
        normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
        if normalized in OrganizationType.__members__:
            return OrganizationType[normalized]
        if normalized.isdigit():
            return OrganizationType(int(normalized))
    raise ValueError(f"Invalid organization type: {value}")


class CreateOrganizationDTO(BaseModel):
    name: str
    shortName: str
    type: OrganizationType
    created_by: str
    description: str | None = None

    @field_validator("type", mode="before")
    def parse_type(cls, value):
        return parse_organization_type(value)


class OrganizationDTO(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    name: str
    shortName: str
    description: str | None = None
    type: int
    createdBy: str

    @property
    def created_by(self) -> str:
        return self.createdBy

    @field_validator("type", mode="before")
    def parse_type(cls, value):
        if isinstance(value, OrganizationType):
            return value.value
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return parse_organization_type(value).value
