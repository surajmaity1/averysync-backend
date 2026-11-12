from django.test import SimpleTestCase

from backend.constants.messages import ValidationErrors
from backend.constants.organization import OrganizationType
from backend.serializers.create_organization_serializer import (
    CreateOrganizationSerializer,
)
from backend.tests.fixtures.organization import (
    organization_type_string_cases,
    valid_create_organization_serializer_payload,
)


class CreateOrganizationSerializerTests(SimpleTestCase):
    def test_valid_payload_with_integer_type(self):
        payload = valid_create_organization_serializer_payload.copy()
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Acme Academy")
        self.assertEqual(serializer.validated_data["shortName"], "acme-academy")
        self.assertNotIn("short_name", serializer.validated_data)
        self.assertEqual(serializer.validated_data["type"], OrganizationType.SCHOOL)
        self.assertEqual(serializer.validated_data["description"], "A premier school")

    def test_valid_payload_with_string_type_names(self):
        for type_input, expected_enum in organization_type_string_cases:
            with self.subTest(type_input=type_input):
                payload = {
                    "name": "Test Org",
                    "shortName": "test-org",
                    "type": type_input,
                }
                serializer = CreateOrganizationSerializer(data=payload)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data["type"], expected_enum)
                self.assertEqual(serializer.validated_data["shortName"], "test-org")

    def test_payload_with_short_name_snake_case_fails(self):
        payload = {
            "name": "Acme Academy",
            "short_name": "acme-academy",
            "type": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("short_name", serializer.errors)
        self.assertIn("shortName", serializer.errors)

    def test_payload_with_types_fails(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "acme-academy",
            "types": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("types", serializer.errors)

    def test_missing_name_fails(self):
        payload = {
            "shortName": "acme",
            "type": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_blank_name_fails(self):
        payload = {
            "name": "   ",
            "shortName": "acme",
            "type": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_missing_short_name_fails(self):
        payload = {
            "name": "Acme Academy",
            "type": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("shortName", serializer.errors)
        self.assertIn(
            ValidationErrors.SHORT_NAME_REQUIRED,
            serializer.errors["shortName"],
        )

    def test_blank_short_name_fails(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "   ",
            "type": 1,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("shortName", serializer.errors)

    def test_missing_type_fails(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "acme",
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_invalid_type_integer_fails(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "acme",
            "type": 99,
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_invalid_type_string_fails(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "acme",
            "type": "HOSPITAL",
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_unknown_fields_fail(self):
        payload = {
            "name": "Acme Academy",
            "shortName": "acme",
            "type": 1,
            "extra_field": "not allowed",
        }
        serializer = CreateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("extra_field", serializer.errors)
