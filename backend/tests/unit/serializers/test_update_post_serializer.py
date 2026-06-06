from unittest import TestCase
from backend.tests.fixtures.post import update_posts_data
from backend.serializers.update_post_serializer import UpdatePostSerializer


class UpdatePostSerializerTests(TestCase):
    def setUp(self):
        self.valid_payload = update_posts_data[0]

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
