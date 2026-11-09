from django.test import SimpleTestCase

from backend.constants.follow import FollowRequestAction
from backend.constants.messages import ValidationErrors
from backend.serializers.follow_request_action_serializer import (
    FollowRequestActionSerializer,
)


class FollowRequestActionSerializerTests(SimpleTestCase):
    def test_valid_accept_action(self):
        serializer = FollowRequestActionSerializer(data={"action": "accept"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["action"], FollowRequestAction.ACCEPT.value
        )

    def test_valid_reject_action(self):
        serializer = FollowRequestActionSerializer(data={"action": "reject"})

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data["action"], FollowRequestAction.REJECT.value
        )

    def test_missing_action_is_invalid(self):
        serializer = FollowRequestActionSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("action", serializer.errors)
        self.assertEqual(
            str(serializer.errors["action"][0]),
            ValidationErrors.FOLLOW_ACTION_REQUIRED,
        )

    def test_empty_action_is_invalid(self):
        serializer = FollowRequestActionSerializer(data={"action": ""})

        self.assertFalse(serializer.is_valid())
        self.assertIn("action", serializer.errors)
        self.assertEqual(
            str(serializer.errors["action"][0]),
            ValidationErrors.FOLLOW_ACTION_INVALID,
        )

    def test_invalid_action_choice_is_rejected(self):
        serializer = FollowRequestActionSerializer(data={"action": "block"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("action", serializer.errors)
        self.assertEqual(
            str(serializer.errors["action"][0]),
            ValidationErrors.FOLLOW_ACTION_INVALID,
        )

    def test_unknown_field_is_rejected(self):
        serializer = FollowRequestActionSerializer(
            data={"action": "accept", "extra": "unexpected"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("extra", serializer.errors)
