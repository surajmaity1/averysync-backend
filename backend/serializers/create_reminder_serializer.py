from rest_framework import serializers


class CreateReminderSerializer(serializers.Serializer):
    isReminderSet = serializers.BooleanField(required=True, error_messages={'invalid': 'reminder must be boolean'},
                                               help_text='Reminder of the Space')
