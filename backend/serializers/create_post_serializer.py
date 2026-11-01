from rest_framework import serializers
from backend.constants.messages import ValidationErrors
from backend.constants.post import PostType


class CreatePostSerializer(serializers.Serializer):
    title = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=3,
        max_length=100,
        help_text="Title of the post",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=300,
        help_text="Description of the post",
    )
    type = serializers.ChoiceField(
        required=False,
        default=PostType.POST.name,
        choices=[type.name for type in PostType],
        help_text="Type of the post (POST, SPACE)",
    )
    isRecorded = serializers.BooleanField(
        required=False,
        default=None,
        allow_null=True,
        help_text="Recording status of the Space",
    )

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(ValidationErrors.TITLE_REQUIRED)
        return value

    def validate(self, data):
        unknown_fields = self.initial_data.keys() - self.fields.keys()

        if unknown_fields:
            raise serializers.ValidationError(
                {field: f"{field} not allowed." for field in unknown_fields}
            )

        post_type = data.get("type", None)

        if post_type not in PostType:
            raise serializers.ValidationError(
                {"type": "type must be either 'POST' or 'SPACE'"}
            )
        return data
