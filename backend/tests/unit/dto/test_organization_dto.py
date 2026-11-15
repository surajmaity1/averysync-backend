import uuid
from django.test import SimpleTestCase

from backend.constants.organization import OrganizationType
from backend.dto.organization_dto import (
    CreateOrganizationDTO,
    OrganizationDTO,
    parse_organization_type,
)
from backend.dto.responses.get_organization_by_id_response import (
    GetOrganizationByIdResponse,
)
from backend.tests.fixtures.organization import organizations_data


class OrganizationDtoAndTypeTests(SimpleTestCase):
    def test_organization_type_enum_definition(self):
        self.assertEqual(OrganizationType.SCHOOL.value, 1)
        self.assertEqual(OrganizationType.COLLEGE.value, 2)
        self.assertEqual(OrganizationType.PRIVATE_TUITION.value, 3)
        self.assertEqual(OrganizationType.PRIVATE_SECTOR.value, 4)

    def test_parse_organization_type_with_enum_instance(self):
        self.assertIs(
            parse_organization_type(OrganizationType.SCHOOL), OrganizationType.SCHOOL
        )

    def test_parse_organization_type_with_integers(self):
        self.assertIs(parse_organization_type(1), OrganizationType.SCHOOL)
        self.assertIs(parse_organization_type(2), OrganizationType.COLLEGE)
        self.assertIs(parse_organization_type(3), OrganizationType.PRIVATE_TUITION)
        self.assertIs(parse_organization_type(4), OrganizationType.PRIVATE_SECTOR)

    def test_parse_organization_type_with_strings(self):
        self.assertIs(parse_organization_type("school"), OrganizationType.SCHOOL)
        self.assertIs(parse_organization_type("COLLEGE"), OrganizationType.COLLEGE)
        self.assertIs(
            parse_organization_type("private tuition"),
            OrganizationType.PRIVATE_TUITION,
        )
        self.assertIs(
            parse_organization_type("private-tuition"),
            OrganizationType.PRIVATE_TUITION,
        )
        self.assertIs(
            parse_organization_type("private sector"), OrganizationType.PRIVATE_SECTOR
        )
        self.assertIs(parse_organization_type("1"), OrganizationType.SCHOOL)

    def test_parse_organization_type_invalid_values(self):
        for invalid in [0, 5, "hospital", "private sctor", True, False, None, object()]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    parse_organization_type(invalid)

    def test_create_organization_dto_parses_type(self):
        dto = CreateOrganizationDTO(
            name="Alpha Corp",
            shortName="alpha-corp",
            type="private sector",
            created_by="user-123",
        )
        self.assertEqual(dto.type, OrganizationType.PRIVATE_SECTOR)
        self.assertEqual(dto.shortName, "alpha-corp")

    def test_organization_dto_parses_type(self):
        sample = organizations_data[0]
        dto = OrganizationDTO(
            id=uuid.UUID(sample["id"]),
            name=sample["name"],
            shortName=sample["shortName"],
            type="school",
            createdBy=sample["createdBy"],
        )
        self.assertEqual(dto.type, OrganizationType.SCHOOL.value)

    def test_get_organization_by_id_response_serialization(self):
        sample = organizations_data[0]
        dto = OrganizationDTO(
            id=uuid.UUID(sample["id"]),
            name=sample["name"],
            shortName=sample["shortName"],
            description=sample["description"],
            type=sample["type"],
            createdBy=sample["createdBy"],
        )
        response = GetOrganizationByIdResponse(data=dto)
        serialized = response.model_dump(mode="json")

        self.assertIn("data", serialized)
        self.assertEqual(serialized["data"]["id"], sample["id"])
        self.assertEqual(serialized["data"]["name"], sample["name"])
        self.assertEqual(serialized["data"]["shortName"], sample["shortName"])
        self.assertEqual(serialized["data"]["description"], sample["description"])
        self.assertEqual(serialized["data"]["type"], sample["type"])
        self.assertEqual(serialized["data"]["createdBy"], sample["createdBy"])
