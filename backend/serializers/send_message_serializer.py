from rest_framework import serializers

from backend.constants.messages import ValidationErrors


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=4000,
        error_messages={
            "required": ValidationErrors.BODY_REQUIRED,
            "null": ValidationErrors.BODY_REQUIRED,
            "blank": ValidationErrors.BODY_REQUIRED,
            "max_length": ValidationErrors.BODY_TOO_LONG,
        },
        help_text="Message text (1-4000 chars)",
    )
    type = serializers.ChoiceField(
        choices=["TEXT"],
        required=False,
        default="TEXT",
        help_text="Message type (only TEXT in v1)",
    )
    clientMessageId = serializers.CharField(
        required=False,
        allow_null=True,
        max_length=64,
        help_text="Idempotency token; a repeat returns the original message",
    )

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()
        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )
        return data
