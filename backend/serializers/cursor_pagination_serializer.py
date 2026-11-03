from rest_framework import serializers

from backend.constants.messages import ValidationErrors


class CursorPaginationSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False,
        default=20,
        min_value=1,
        max_value=100,
        error_messages={
            "min_value": ValidationErrors.PAGINATION_LIMIT_INVALID,
            "max_value": ValidationErrors.PAGINATION_LIMIT_INVALID,
        },
        help_text="Page size (1-100)",
    )
    cursor = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        help_text="Opaque cursor '<iso>|<uuid>' from a previous page",
    )
