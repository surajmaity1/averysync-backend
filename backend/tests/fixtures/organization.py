import uuid
from backend.constants.organization import OrganizationType
from backend.dto.organization_dto import CreateOrganizationDTO, OrganizationDTO

organizations_data = [
    {
        "id": "7a94ef88-29cb-4a25-a1c1-4b150965d111",
        "name": "Springfield Elementary",
        "shortName": "springfield-elem",
        "description": "Public elementary school",
        "type": OrganizationType.SCHOOL.value,
        "createdBy": "9dee2457-9d0b-4bd8-a509-abaaaf618cfa",
    },
    {
        "id": "bb462881-2c67-4bb4-bb66-7d636830501a",
        "name": "Tech University",
        "shortName": "tech-uni",
        "description": "Engineering college",
        "type": OrganizationType.COLLEGE.value,
        "createdBy": "9dee2457-9d0b-4bd8-a509-abaaaf618cfa",
    },
]

valid_create_organization_payload = {
    "name": "Tech University",
    "shortName": "tech-uni",
    "type": OrganizationType.COLLEGE.value,
    "description": "Engineering college",
}

valid_create_organization_serializer_payload = {
    "name": "Acme Academy",
    "shortName": "acme-academy",
    "type": 1,
    "description": "A premier school",
}

organization_type_string_cases = [
    ("SCHOOL", OrganizationType.SCHOOL),
    ("COLLEGE", OrganizationType.COLLEGE),
    ("PRIVATE_TUITION", OrganizationType.PRIVATE_TUITION),
    ("PRIVATE_SECTOR", OrganizationType.PRIVATE_SECTOR),
    ("PRIVATE SECTOR", OrganizationType.PRIVATE_SECTOR),
    ("PRIVATE TUITION", OrganizationType.PRIVATE_TUITION),
]


def build_organization_dto(
    caller_id: str | None = None,
    org_id: uuid.UUID | None = None,
    name: str = "Tech University",
    short_name: str = "tech-uni",
    description: str | None = "Engineering college",
    org_type: int = OrganizationType.COLLEGE.value,
) -> OrganizationDTO:
    return OrganizationDTO(
        id=org_id or uuid.uuid4(),
        name=name,
        shortName=short_name,
        description=description,
        type=org_type,
        createdBy=caller_id or str(uuid.uuid4()),
    )


def build_create_organization_dto(
    caller_id: str | None = None,
    name: str = "Apex Institute",
    short_name: str = "apex-inst",
    description: str | None = "Coaching institute",
    org_type: OrganizationType = OrganizationType.PRIVATE_TUITION,
) -> CreateOrganizationDTO:
    return CreateOrganizationDTO(
        name=name,
        shortName=short_name,
        description=description,
        type=org_type,
        created_by=caller_id or str(uuid.uuid4()),
    )
