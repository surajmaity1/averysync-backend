from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.constants.messages import ApiErrors
from backend.dto.organization_dto import CreateOrganizationDTO, UpdateOrganizationDTO
from backend.dto.responses.error_response import (
    ApiErrorDetail,
    ApiErrorResponse,
    ApiErrorSource,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateForbiddenException,
)
from backend.serializers.create_organization_serializer import (
    CreateOrganizationSerializer,
)
from backend.serializers.update_organization_serializer import (
    UpdateOrganizationSerializer,
)
from backend.services.organization_service import OrganizationService
from backend.utils.uuid_validation import validate_uuid


class OrganizationErrorMixin:
    def _error(self, status_code: int, message: str, exception: Exception) -> Response:
        error_response = ApiErrorResponse(
            statusCode=status_code,
            message=message,
            errors=[
                ApiErrorDetail(
                    title=message,
                    description=str(exception) if settings.DEBUG else message,
                )
            ]
            if settings.ERROR_DETAILS
            else message,
        )
        return Response(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status_code,
        )

    def _validation_error(self, errors) -> Response:
        formatted_errors = [
            ApiErrorDetail(
                source={ApiErrorSource.PARAMETER: field},
                title=ApiErrors.VALIDATION_ERROR,
                description=str(messages),
            )
            for field, messages in errors.items()
        ]
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_400_BAD_REQUEST,
            message=ApiErrors.VALIDATION_ERROR,
            errors=formatted_errors,
        )
        return Response(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _message_of(self, exception: Exception) -> str:
        return getattr(exception, "message", None) or str(exception)

    def _handle_domain_exception(self, exception: Exception) -> Response:
        if isinstance(exception, OrganizationAlreadyExistsException):
            return self._error(
                status.HTTP_409_CONFLICT, self._message_of(exception), exception
            )
        if isinstance(exception, OrganizationNotFoundException):
            return self._error(
                status.HTTP_404_NOT_FOUND, self._message_of(exception), exception
            )
        if isinstance(exception, OrganizationUpdateForbiddenException):
            return self._error(
                status.HTTP_403_FORBIDDEN, self._message_of(exception), exception
            )
        return self._error(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ApiErrors.UNEXPECTED_ERROR_OCCURRED,
            exception,
        )


class OrganizationsView(OrganizationErrorMixin, APIView):
    def post(self, request: Request) -> Response:
        serializer = CreateOrganizationSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        try:
            dto = CreateOrganizationDTO(
                **serializer.validated_data,
                created_by=str(request.user_id),
            )
            response = OrganizationService.create_organization(dto)
            return Response(
                data=response.model_dump(mode="json"),
                status=status.HTTP_201_CREATED,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)

    def get(self, request: Request) -> Response:
        try:
            response = OrganizationService.get_all_organizations()
            return Response(
                data=response.model_dump(mode="json"),
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class OrganizationDetailView(OrganizationErrorMixin, APIView):
    def patch(self, request: Request, organization_id) -> Response:
        org_id_str = str(organization_id)
        if not validate_uuid(uuid_string=org_id_str):
            return self._handle_domain_exception(
                OrganizationNotFoundException(org_id=org_id_str)
            )

        serializer = UpdateOrganizationSerializer(data=request.data)
        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        try:
            dto = UpdateOrganizationDTO(**serializer.validated_data)
            response = OrganizationService.update_organization(
                org_id=org_id_str,
                user_id=str(request.user_id),
                dto=dto,
            )
            return Response(
                data=response.model_dump(mode="json"),
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)
