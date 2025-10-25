from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from backend.constants.messages import ApiErrors
from backend.dto.post_dto import CreatePostDTO
from backend.dto.responses.create_post_response import CreatePostResponse
from backend.dto.responses.error_response import ApiErrorDetail, ApiErrorSource, ApiErrorResponse
from backend.serializers.create_post_serializer import CreatePostSerializer
from backend.services.post_service import PostService
from rest_framework import status
from django.conf import settings


class PostView(APIView):
    def post(self, request: Request):
        try:
            serializer = CreatePostSerializer(data=request.data)

            if not serializer.is_valid():
                return self._handle_validation_error(serializer.errors)

            dto = CreatePostDTO(**serializer.validated_data, created_by=request.user_id)
            response: CreatePostResponse = PostService.create_post(dto)
            
            return Response(data=response.model_dump(mode='json'), status=status.HTTP_201_CREATED)
        except ValueError as exception:
            error_response = exception.args[0]
            if isinstance(error_response, ApiErrorResponse):
                return Response(data=error_response.model_dump(mode='json'), status=error_response.statusCode)

            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ]
            )
            return Response(
                data=api_error_response.model_dump(mode='json'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    def _handle_validation_error(self, errors):
        formatted_errors = []

        for fields, messages in errors.items():
            formatted_errors.append(
                ApiErrorDetail(source={ApiErrorSource.PARAMETER: fields}, title=ApiErrors.VALIDATION_ERROR,
                               description=str(messages)))

        error_response = ApiErrorResponse(statusCode=400, message=ApiErrors.VALIDATION_ERROR, errors=formatted_errors)
        return Response(data=error_response.model_dump(mode='json'), status=status.HTTP_400_BAD_REQUEST)
