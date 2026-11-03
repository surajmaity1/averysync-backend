from rest_framework import serializers

from backend.constants.messages import ValidationErrors


class MuteParticipantSerializer(serializers.Serializer):
    isMuted = serializers.BooleanField(
        required=True,
        error_messages={"invalid": "isMuted must be boolean"},
        help_text="Declarative mute state for the participant",
    )
    durationSeconds = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=86400,
        error_messages={
            "min_value": ValidationErrors.DURATION_SECONDS_INVALID,
            "max_value": ValidationErrors.DURATION_SECONDS_INVALID,
        },
        help_text="Temporary mute duration in seconds (1-86400)",
    )
    reason = serializers.CharField(
        required=False,
        max_length=300,
        help_text="Optional moderation reason",
    )

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()

        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )

        if not data["isMuted"] and ("durationSeconds" in data or "reason" in data):
            raise serializers.ValidationError(ValidationErrors.MUTE_FIELDS_NOT_ALLOWED)

        return data
