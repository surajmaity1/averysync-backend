from unittest import TestCase
import unittest
from backend.tests.fixtures.post import update_posts_data
from backend.serializers.post_serializer import UpdatePostSerializer


class UpdatePostSerializerTests(TestCase):
    def setUp(self):
        self.valid_payload = update_posts_data[0]

    @unittest.skip("temporariy")
    def test_empty_payload_for_updating_post(self):
        serializer = UpdatePostSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors)

    def test_valid_title_status_payload(self):
        serializer = UpdatePostSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid())
        self.assertFalse(serializer.errors)

    def test_invalid_status_payload(self):
        data = self.valid_payload.copy()
        data["status"] = "OPEN"
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors)
        self.assertIn(
            f'"{data["status"]}" is not a valid choice.', serializer.errors["status"]
        )

    def test_restrict_type_field_in_payload(self):
        data = self.valid_payload.copy()
        data["type"] = "SPACE"
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("type not allowed", serializer.errors["type"])

    def test_update_invalid_title_less_than_required_length(self):
        data = self.valid_payload.copy()
        data["title"] = "BL"
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has at least 3 characters.", serializer.errors["title"]
        )

    def test_update_invalid_title_greater_than_required_length(self):
        data = self.valid_payload.copy()
        data["title"] = "a" * 101
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has no more than 100 characters.",
            serializer.errors["title"],
        )

    def test_fields_should_not_be_blank(self):
        data = self.valid_payload.copy()
        data["title"] = ""
        data["description"] = ""
        data["isRecorded"] = ""
        data["scheduledStartedAt"] = ""
        data["scheduledEndedAt"] = ""
        data["startedAt"] = ""
        data["endedAt"] = ""
        data["createdInTimezone"] = ""
        data["status"] = ""
        data["type"] = ""
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("This field may not be blank.", serializer.errors["title"])
        self.assertIn("This field may not be blank.", serializer.errors["description"])
        self.assertIn("Must be a valid boolean.", serializer.errors["isRecorded"])
        self.assertIn(
            "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].",
            serializer.errors["scheduledStartedAt"],
        )
        self.assertIn(
            "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].",
            serializer.errors["scheduledEndedAt"],
        )
        self.assertIn(
            "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].",
            serializer.errors["startedAt"],
        )
        self.assertIn(
            "Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].",
            serializer.errors["endedAt"],
        )
        self.assertIn(
            "This field may not be blank.", serializer.errors["createdInTimezone"]
        )
        self.assertIn('"" is not a valid choice.', serializer.errors["status"])
        self.assertIn('"" is not a valid choice.', serializer.errors["type"])

    def test_update_invalid_description_greater_than_required_length(self):
        data = self.valid_payload.copy()
        data["description"] = "a" * 301
        serializer = UpdatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has no more than 300 characters.",
            serializer.errors["description"],
        )
