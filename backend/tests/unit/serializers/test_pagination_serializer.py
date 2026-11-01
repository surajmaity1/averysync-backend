from django.test import SimpleTestCase

from backend.serializers.pagination_serializer import PaginationSerializer


class PaginationSerializerTests(SimpleTestCase):
    def test_defaults_applied_when_absent(self):
        serializer = PaginationSerializer(data={})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["limit"], 20)
        self.assertEqual(serializer.validated_data["offset"], 0)

    def test_valid_limit_and_offset(self):
        serializer = PaginationSerializer(data={"limit": 50, "offset": 10})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["limit"], 50)
        self.assertEqual(serializer.validated_data["offset"], 10)

    def test_limit_above_max_is_invalid(self):
        serializer = PaginationSerializer(data={"limit": 101})

        self.assertFalse(serializer.is_valid())
        self.assertIn("limit", serializer.errors)

    def test_limit_below_min_is_invalid(self):
        serializer = PaginationSerializer(data={"limit": 0})

        self.assertFalse(serializer.is_valid())
        self.assertIn("limit", serializer.errors)

    def test_negative_offset_is_invalid(self):
        serializer = PaginationSerializer(data={"offset": -1})

        self.assertFalse(serializer.is_valid())
        self.assertIn("offset", serializer.errors)
