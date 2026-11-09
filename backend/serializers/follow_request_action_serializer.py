from rest_framework import serializers

from backend.constants.follow import FollowRequestAction
from backend.constants.messages import ValidationErrors


class FollowRequestActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[action.value for action in FollowRequestAction],
        required=True,
        error_messages={
            "required": ValidationErrors.FOLLOW_ACTION_REQUIRED,
            "null": ValidationErrors.FOLLOW_ACTION_REQUIRED,
            "blank": ValidationErrors.FOLLOW_ACTION_REQUIRED,
            "invalid_choice": ValidationErrors.FOLLOW_ACTION_INVALID,
        },
        help_text="Action to perform on the follow request ('accept' or 'reject')",
    )

    def validate(self, data):
        if hasattr(self.initial_data, "keys"):
            unknown_fields = self.initial_data.keys() - self.fields.keys()
            if unknown_fields:
                raise serializers.ValidationError(
                    {field: f"{field} not allowed." for field in unknown_fields}
                )
        return data
