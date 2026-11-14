from rest_framework import serializers

from backend.constants.messages import ValidationErrors
from backend.dto.organization_dto import parse_organization_type
from backend.serializers.create_organization_serializer import OrganizationTypeField


class UpdateOrganizationSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        allow_blank=False,
        min_length=3,
        max_length=255,
        error_messages={
            "blank": ValidationErrors.ORGANIZATION_NAME_REQUIRED,
        },
        help_text="Updated name of the organization",
    )
    shortName = serializers.CharField(
        required=False,
        allow_blank=False,
        min_length=3,
        max_length=100,
        error_messages={
            "blank": ValidationErrors.SHORT_NAME_REQUIRED,
        },
        help_text="Updated unique short name of the organization in camelCase",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=1000,
        help_text="Updated description of the organization",
    )
    type = OrganizationTypeField(
        required=False,
        help_text="Updated type of the organization (1: SCHOOL, 2: COLLEGE, 3: PRIVATE_TUITION, 4: PRIVATE_SECTOR)",
    )

    def to_internal_value(self, data):
        errors = {}
        if hasattr(data, "keys"):
            unknown_fields = data.keys() - self.fields.keys()
            if unknown_fields:
                for field in unknown_fields:
                    errors[field] = f"{field} not allowed."
        try:
            validated = super().to_internal_value(data)
        except serializers.ValidationError as exc:
            errors.update(exc.detail)
        if errors:
            raise serializers.ValidationError(errors)
        return validated

    def validate_name(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError(
                ValidationErrors.ORGANIZATION_NAME_REQUIRED
            )
        return trimmed

    def validate_shortName(self, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise serializers.ValidationError(ValidationErrors.SHORT_NAME_REQUIRED)
        return trimmed

    def validate(self, data):
        initial = getattr(self, "initial_data", {})
        if "type" in initial or "type" in data:
            raw_type = initial.get("type") if "type" in initial else data.get("type")
            if raw_type is None:
                raise serializers.ValidationError(
                    {"type": ValidationErrors.ORGANIZATION_TYPE_INVALID}
                )
            try:
                parsed_type = parse_organization_type(raw_type)
                data["type"] = parsed_type
            except (ValueError, KeyError):
                raise serializers.ValidationError(
                    {"type": ValidationErrors.ORGANIZATION_TYPE_INVALID}
                )

        return data
