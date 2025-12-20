from rest_framework import serializers
from backend.constants.post import PostType, SpaceStatus


class UpdatePostSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=False, default=None, help_text='Title of the post')
    description = serializers.CharField(required=False, default=None, allow_null=True,
                                        help_text='Description of the post')
    isRecorded = serializers.BooleanField(required=False, default=None, help_text='Recording status of the Space')
    scheduledStartedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                                   help_text='scheduled starting datetime of the Space')
    scheduledEndedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                                 help_text='scheduled ending datetime of the Space')
    startedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                          help_text='starting datetime of the Space')
    endedAt = serializers.DateTimeField(required=False, default=None, allow_null=True,
                                        help_text='ending datetime of the Space')
    createdInTimezone = serializers.CharField(required=False, default=None,
                                              help_text='Timezone at the time of the post or space creation')
    status = serializers.CharField(required=False, default=None, help_text='Status of the space')
    type = serializers.ChoiceField(required=False, default=None, choices=[type.name for type in PostType],
                                   help_text='Type of the post (POST, SPACE)')

    def validate(self, data):

        unknown_fields = self.initial_data.keys() - self.fields.keys()

        if unknown_fields:
            raise serializers.ValidationError(
                {field: f'{field} not allowed.' for field in unknown_fields}
            )

        post_type = data.get('type', None)
        post_status = data.get('status', None)

        if post_type:
            raise serializers.ValidationError({f'type': 'Type of the post or space not allowed'})

        if post_status and post_status not in SpaceStatus.__members__:
            raise serializers.ValidationError({f'status': "status must be either 'OPEN' or 'CLOSED'"})

        return data
