from rest_framework import serializers

from backend.constants.messages import ValidationErrors
from backend.constants.post import PostType, SpaceStatus


class CreatePostSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False, help_text='Title of the post')
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True,
                                        help_text='Description of the post')
    type = serializers.ChoiceField(required=False, default=PostType.POST.name, choices=[type.name for type in PostType],
                                   help_text='Type of the post (POST, SPACE)')
    isRecorded = serializers.BooleanField(required=False, default=None, allow_null=True,
                                          help_text='Recording status of the Space')

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(ValidationErrors.TITLE_REQUIRED)
        return value

    def validate(self, data):
        post_type = data.get('type', None)

        if post_type not in PostType:
            raise serializers.ValidationError({f'type': "type must be either 'POST' or 'SPACE'"})
        return data


class UpdatePostSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, default=None, help_text='Title of the post')
    description = serializers.CharField(required=False, default=None, allow_null=True,
                                        help_text='Description of the post')
    isRecorded = serializers.BooleanField(required=False, default=None, allow_null=True,
                                          help_text='Recording status of the Space')
    scheduledStartedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                                   help_text='scheduled starting datetime of the Space')
    scheduledEndedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                                 help_text='scheduled ending datetime of the Space')
    startedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                          help_text='starting datetime of the Space')
    endedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                        help_text='ending datetime of the Space')
    createdInTimezone = serializers.CharField(required=False, default=None, help_text='Timezone at the time of the post or space creation')
    status = serializers.CharField(required=False, default=None, help_text='Status of the space')
    type = serializers.ChoiceField(required=False, default=None, choices=[type.name for type in PostType],
                                   help_text='Type of the post (POST, SPACE)')

    def validate(self, data):
        post_type = data.get('type', None)
        post_status = data.get('status', None)
        
        if post_type:
            raise serializers.ValidationError({f'type': 'Type of the post or space not allowed'})

        if post_status and post_status not in SpaceStatus.__members__:
            raise serializers.ValidationError({f'status': "status must be either 'OPEN' or 'CLOSED'"})

        return data
