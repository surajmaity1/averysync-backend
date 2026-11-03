import uuid

from django.test import SimpleTestCase

from backend.serializers.create_conversation_serializer import (
    CreateConversationSerializer,
)


class CreateConversationSerializerTests(SimpleTestCase):
    def test_valid_direct_payload(self):
        participant = str(uuid.uuid4())
        serializer = CreateConversationSerializer(
            data={"type": "DIRECT", "participantId": participant}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(str(serializer.validated_data["participantId"]), participant)

    def test_type_defaults_to_direct(self):
        serializer = CreateConversationSerializer(
            data={"participantId": str(uuid.uuid4())}
        )

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["type"], "DIRECT")

    def test_missing_participant_is_invalid(self):
        serializer = CreateConversationSerializer(data={"type": "DIRECT"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("participantId", serializer.errors)

    def test_group_type_is_rejected(self):
        serializer = CreateConversationSerializer(
            data={"type": "GROUP", "participantId": str(uuid.uuid4())}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)

    def test_unknown_field_is_rejected(self):
        serializer = CreateConversationSerializer(
            data={"participantId": str(uuid.uuid4()), "extra": "nope"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("extra", serializer.errors)
