from rest_framework import serializers


class UpdateProfileSerializer(serializers.Serializer):
    isPrivate = serializers.BooleanField(
        required=True,
        error_messages={
            "required": "isPrivate is required",
            "null": "isPrivate is required",
            "invalid": "isPrivate must be boolean",
        },
        help_text="Whether the profile is private",
    )

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()

        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )

        return data
