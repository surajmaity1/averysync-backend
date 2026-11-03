from rest_framework import serializers

from backend.constants.messages import ValidationErrors


class PaginationSerializer(serializers.Serializer):
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
    offset = serializers.IntegerField(
        required=False,
        default=0,
        min_value=0,
        error_messages={"min_value": ValidationErrors.PAGINATION_OFFSET_INVALID},
        help_text="Number of rows to skip",
    )
