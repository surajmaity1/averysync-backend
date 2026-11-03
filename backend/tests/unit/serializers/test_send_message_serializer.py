from django.test import SimpleTestCase

from backend.serializers.send_message_serializer import SendMessageSerializer


class SendMessageSerializerTests(SimpleTestCase):
    def test_valid_body(self):
        serializer = SendMessageSerializer(data={"body": "hey there"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["body"], "hey there")
        self.assertEqual(serializer.validated_data["type"], "TEXT")

    def test_blank_body_is_invalid(self):
        serializer = SendMessageSerializer(data={"body": "   "})

        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)

    def test_missing_body_is_invalid(self):
        serializer = SendMessageSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)

    def test_oversized_body_is_invalid(self):
        serializer = SendMessageSerializer(data={"body": "x" * 4001})

        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)

    def test_client_message_id_is_optional_and_kept(self):
        serializer = SendMessageSerializer(
            data={"body": "hi", "clientMessageId": "c-123"}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["clientMessageId"], "c-123")

    def test_unknown_field_is_rejected(self):
        serializer = SendMessageSerializer(data={"body": "hi", "extra": 1})

        self.assertFalse(serializer.is_valid())
        self.assertIn("extra", serializer.errors)
