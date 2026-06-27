from unittest import TestCase

from backend.constants.post import PostType
from backend.serializers.create_post_serializer import CreatePostSerializer


class CreatePostSerializerTests(TestCase):
    def setUp(self):
        self.valid_payload = {
            "title": "BLR Meetup",
            "description": "HSR Layout",
            "type": PostType.SPACE.name,
            "isRecorded": True,
        }

    def test_valid_payload(self):
        serializer = CreatePostSerializer(data=self.valid_payload)
        self.assertTrue(serializer.is_valid())
        self.assertFalse(serializer.errors)

    def test_minimal_payload_with_only_title(self):
        serializer = CreatePostSerializer(data={"title": "Meetup"})
        self.assertTrue(serializer.is_valid())
        self.assertFalse(serializer.errors)

    def test_type_defaults_to_post_when_omitted(self):
        serializer = CreatePostSerializer(data={"title": "Meetup"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["type"], PostType.POST.name)

    def test_isRecorded_defaults_to_none_when_omitted(self):
        serializer = CreatePostSerializer(data={"title": "Meetup"})
        self.assertTrue(serializer.is_valid())
        self.assertIsNone(serializer.validated_data["isRecorded"])

    def test_title_is_required(self):
        data = self.valid_payload.copy()
        del data["title"]
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("This field is required.", serializer.errors["title"])

    def test_title_may_not_be_blank(self):
        data = self.valid_payload.copy()
        data["title"] = ""
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("This field may not be blank.", serializer.errors["title"])

    def test_whitespace_only_title_rejected(self):
        data = self.valid_payload.copy()
        data["title"] = "   "
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("This field may not be blank.", serializer.errors["title"])

    def test_title_below_min_length(self):
        data = self.valid_payload.copy()
        data["title"] = "BL"
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has at least 3 characters.", serializer.errors["title"]
        )

    def test_title_above_max_length(self):
        data = self.valid_payload.copy()
        data["title"] = "a" * 101
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has no more than 100 characters.",
            serializer.errors["title"],
        )

    def test_description_above_max_length(self):
        data = self.valid_payload.copy()
        data["description"] = "a" * 301
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "Ensure this field has no more than 300 characters.",
            serializer.errors["description"],
        )

    def test_description_allows_blank_and_null(self):
        for value in ("", None):
            data = self.valid_payload.copy()
            data["description"] = value
            serializer = CreatePostSerializer(data=data)
            self.assertTrue(serializer.is_valid(), msg=f"failed for {value!r}")

    def test_invalid_type_choice(self):
        data = self.valid_payload.copy()
        data["type"] = "ARTICLE"
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('"ARTICLE" is not a valid choice.', serializer.errors["type"])

    def test_invalid_isRecorded_value(self):
        data = self.valid_payload.copy()
        data["isRecorded"] = "not-a-bool"
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Must be a valid boolean.", serializer.errors["isRecorded"])

    def test_unknown_field_not_allowed(self):
        data = self.valid_payload.copy()
        data["unexpected"] = "value"
        serializer = CreatePostSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("unexpected not allowed.", serializer.errors["unexpected"])
