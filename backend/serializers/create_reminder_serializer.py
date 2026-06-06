from rest_framework import serializers


class CreateReminderSerializer(serializers.Serializer):
    isReminderSet = serializers.BooleanField(
        required=True,
        error_messages={"invalid": "reminder must be boolean"},
        help_text="Reminder of the Space",
    )

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()

        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )

        return data
