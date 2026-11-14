from django.test import SimpleTestCase

from backend.constants.organization import OrganizationType
from backend.serializers.update_organization_serializer import (
    UpdateOrganizationSerializer,
)
from backend.tests.fixtures.organization import organization_type_string_cases


class UpdateOrganizationSerializerTests(SimpleTestCase):
    def test_valid_partial_payload_name_only(self):
        payload = {"name": "Updated Org Name"}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Updated Org Name")
        self.assertNotIn("shortName", serializer.validated_data)
        self.assertNotIn("type", serializer.validated_data)
        self.assertNotIn("description", serializer.validated_data)

    def test_valid_partial_payload_short_name_only(self):
        payload = {"shortName": "updated-short-name"}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["shortName"], "updated-short-name")

    def test_valid_partial_payload_type_only(self):
        payload = {"type": OrganizationType.COLLEGE.value}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["type"], OrganizationType.COLLEGE)

    def test_valid_payload_with_string_type_names(self):
        for type_input, expected_enum in organization_type_string_cases:
            with self.subTest(type_input=type_input):
                payload = {"type": type_input}
                serializer = UpdateOrganizationSerializer(data=payload)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(serializer.validated_data["type"], expected_enum)

    def test_valid_partial_payload_description_null(self):
        payload = {"description": None}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.validated_data["description"])

    def test_payload_with_short_name_snake_case_fails(self):
        payload = {"short_name": "snake-case-name"}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("short_name", serializer.errors)

    def test_blank_name_fails(self):
        payload = {"name": "   "}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_blank_short_name_fails(self):
        payload = {"shortName": "   "}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("shortName", serializer.errors)

    def test_invalid_type_integer_fails(self):
        payload = {"type": 99}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_invalid_type_string_fails(self):
        payload = {"type": "NON_EXISTENT_TYPE"}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_unknown_fields_fail(self):
        payload = {"name": "Acme", "extra": "not-allowed"}
        serializer = UpdateOrganizationSerializer(data=payload)
        self.assertFalse(serializer.is_valid())
        self.assertIn("extra", serializer.errors)
