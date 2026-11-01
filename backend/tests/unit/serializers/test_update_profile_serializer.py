from django.test import SimpleTestCase

from backend.serializers.update_profile_serializer import UpdateProfileSerializer


class UpdateProfileSerializerTests(SimpleTestCase):
    def test_valid_is_private_true(self):
        serializer = UpdateProfileSerializer(data={"isPrivate": True})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"isPrivate": True})

    def test_valid_is_private_false(self):
        serializer = UpdateProfileSerializer(data={"isPrivate": False})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, {"isPrivate": False})

    def test_missing_is_private_is_invalid(self):
        serializer = UpdateProfileSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("isPrivate", serializer.errors)

    def test_non_boolean_is_private_is_invalid(self):
        serializer = UpdateProfileSerializer(data={"isPrivate": "maybe"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("isPrivate", serializer.errors)

    def test_unknown_field_is_rejected(self):
        serializer = UpdateProfileSerializer(data={"isPrivate": True, "isPublic": True})

        self.assertFalse(serializer.is_valid())
        self.assertIn("isPublic", serializer.errors)
