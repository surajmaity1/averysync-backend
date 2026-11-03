from rest_framework import serializers

from backend.constants.messages import ValidationErrors


class CreateConversationSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=["DIRECT"],
        required=False,
        default="DIRECT",
        error_messages={"invalid_choice": ValidationErrors.CONVERSATION_TYPE_INVALID},
        help_text="Conversation type (only DIRECT in v1)",
    )
    participantId = serializers.UUIDField(
        required=True,
        error_messages={
            "required": ValidationErrors.PARTICIPANT_ID_REQUIRED,
            "null": ValidationErrors.PARTICIPANT_ID_REQUIRED,
            "invalid": ValidationErrors.PARTICIPANT_ID_REQUIRED,
        },
        help_text="The other participant's user id",
    )

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()
        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )
        return data
