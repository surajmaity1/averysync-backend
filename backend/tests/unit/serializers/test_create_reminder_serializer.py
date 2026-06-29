from unittest import TestCase

from backend.serializers.create_reminder_serializer import CreateReminderSerializer


class CreateReminderSerializerTests(TestCase):
    def test_valid_payload_true(self):
        serializer = CreateReminderSerializer(data={"isReminderSet": True})
        self.assertTrue(serializer.is_valid())
        self.assertFalse(serializer.errors)
        self.assertTrue(serializer.validated_data["isReminderSet"])

    def test_valid_payload_false(self):
        serializer = CreateReminderSerializer(data={"isReminderSet": False})
        self.assertTrue(serializer.is_valid())
        self.assertFalse(serializer.validated_data["isReminderSet"])

    def test_isReminderSet_is_required(self):
        serializer = CreateReminderSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn("This field is required.", serializer.errors["isReminderSet"])

    def test_invalid_boolean_uses_custom_message(self):
        serializer = CreateReminderSerializer(data={"isReminderSet": "not-a-bool"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("reminder must be boolean", serializer.errors["isReminderSet"])

    def test_blank_value_rejected(self):
        serializer = CreateReminderSerializer(data={"isReminderSet": ""})
        self.assertFalse(serializer.is_valid())
        self.assertTrue(serializer.errors)

    def test_unknown_field_not_allowed(self):
        serializer = CreateReminderSerializer(
            data={"isReminderSet": True, "unexpected": "value"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("unexpected not allowed.", serializer.errors["unexpected"])
