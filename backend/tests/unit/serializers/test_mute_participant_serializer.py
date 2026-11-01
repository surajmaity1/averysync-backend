from django.test import SimpleTestCase

from backend.constants.messages import ValidationErrors
from backend.serializers.mute_participant_serializer import MuteParticipantSerializer


class MuteParticipantSerializerTests(SimpleTestCase):
    def test_valid_payloads_are_accepted(self):
        valid_payloads = [
            ("permanent_mute", {"isMuted": True}),
            ("temporary_mute", {"isMuted": True, "durationSeconds": 600}),
            (
                "temporary_mute_with_reason",
                {"isMuted": True, "durationSeconds": 600, "reason": "background noise"},
            ),
            ("permanent_mute_with_reason", {"isMuted": True, "reason": "spam"}),
            ("duration_lower_bound", {"isMuted": True, "durationSeconds": 1}),
            ("duration_upper_bound", {"isMuted": True, "durationSeconds": 86400}),
            ("unmute", {"isMuted": False}),
        ]

        for case, payload in valid_payloads:
            with self.subTest(case=case):
                serializer = MuteParticipantSerializer(data=payload)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                self.assertEqual(
                    serializer.validated_data["isMuted"], payload["isMuted"]
                )

    def test_is_muted_is_required(self):
        serializer = MuteParticipantSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("isMuted", serializer.errors)

    def test_non_boolean_is_muted_is_rejected(self):
        serializer = MuteParticipantSerializer(data={"isMuted": "loud"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("isMuted", serializer.errors)

    def test_duration_out_of_range_is_rejected(self):
        for case, duration in [
            ("below_minimum", 0),
            ("negative", -60),
            ("above_maximum", 86401),
        ]:
            with self.subTest(case=case):
                serializer = MuteParticipantSerializer(
                    data={"isMuted": True, "durationSeconds": duration}
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("durationSeconds", serializer.errors)
                self.assertIn(
                    ValidationErrors.DURATION_SECONDS_INVALID,
                    str(serializer.errors["durationSeconds"]),
                )

    def test_non_integer_duration_is_rejected(self):
        serializer = MuteParticipantSerializer(
            data={"isMuted": True, "durationSeconds": "ten"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("durationSeconds", serializer.errors)

    def test_mute_fields_with_unmute_are_rejected(self):
        for case, payload in [
            ("duration_with_unmute", {"isMuted": False, "durationSeconds": 600}),
            ("reason_with_unmute", {"isMuted": False, "reason": "noise"}),
            (
                "both_with_unmute",
                {"isMuted": False, "durationSeconds": 600, "reason": "noise"},
            ),
        ]:
            with self.subTest(case=case):
                serializer = MuteParticipantSerializer(data=payload)
                self.assertFalse(serializer.is_valid())
                self.assertIn(
                    ValidationErrors.MUTE_FIELDS_NOT_ALLOWED, str(serializer.errors)
                )

    def test_reason_longer_than_300_chars_is_rejected(self):
        serializer = MuteParticipantSerializer(
            data={"isMuted": True, "reason": "x" * 301}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("reason", serializer.errors)

    def test_unknown_fields_are_rejected(self):
        serializer = MuteParticipantSerializer(data={"isMuted": True, "volume": 11})

        self.assertFalse(serializer.is_valid())
        self.assertIn("volume", serializer.errors)
