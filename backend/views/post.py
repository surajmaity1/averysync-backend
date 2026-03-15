import uuid

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from backend.constants.messages import ApiErrors
from backend.dto.post_dto import CreatePostDTO, UpdatePostDTO
from backend.dto.responses.create_post_response import CreatePostResponse
from backend.dto.responses.error_response import ApiErrorDetail, ApiErrorSource, ApiErrorResponse
from backend.serializers.create_post_serializer import CreatePostSerializer
from backend.serializers.update_post_serializer import UpdatePostSerializer
from backend.services.post_service import PostService
from django.conf import settings
from backend.exceptions.post_exception import PostNotFoundException, PostUpdateForbidden, PostAlreadyDeletedException
from backend.dto.responses.get_post_by_id_response import GetPostByIdResponse
from backend.utils.uuid_validation import validate_uuid
from backend.serializers.create_reminder_serializer import CreateReminderSerializer
from backend.services.reminder_service import ReminderService
from backend.dto.reminder_dto import CreateUpdateReminderDTO
from backend.dto.responses.get_reminder_by_space_id_response import GetReminderBySpaceIdResponse
from backend.exceptions.reminder_exception import ReminderNotFoundException


class PostView(APIView):
    def post(self, request: Request):
        try:
            serializer = CreatePostSerializer(data=request.data)

            if not serializer.is_valid():
                return self._handle_validation_error(serializer.errors)

            dto = CreatePostDTO(**serializer.validated_data, created_by=request.user_id)
            response: CreatePostResponse = PostService.create_post(dto)

            reminder_dto = CreateUpdateReminderDTO(space_id=response.data.id, isReminderSet=True,
                                                   created_by=request.user_id)
            ReminderService.create_or_update(reminder_dto)

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
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
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

    def get(self, request: Request):
        try:
            response = PostService.get_posts()

            if response.errors:
                if response.errors.get('code') == '400':
                    return Response(data=response.model_dump(mode='json'), status=status.HTTP_400_BAD_REQUEST)
                if response.errors.get('code') == '500':
                    return Response(data=response.model_dump(mode='json'), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(data=response.model_dump(mode='json'), status=status.HTTP_200_OK)
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(data=api_error_response.model_dump(mode='json'),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PostDetailView(APIView):
    def get(self, request: Request, post_id: str):
        try:
            validate_post_id = validate_uuid(uuid_string=post_id)

            if not validate_post_id:
                raise ValueError(f'post not found {post_id}')

            post_dto = PostService.get_post_by_id(post_id)
            response_data = GetPostByIdResponse(data=post_dto)
            return Response(data=response_data.model_dump(mode='json'), status=status.HTTP_200_OK)
        except (PostNotFoundException, ValueError) as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_404_NOT_FOUND,
                message=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                        description=(
                            str(exception) if settings.DEBUG else ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id)),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_NOT_FOUND
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request: Request, post_id: str):
        try:
            validate_post_id = validate_uuid(uuid_string=post_id)

            if not validate_post_id:
                raise ValueError(f'post not found {post_id}')

            serializer = UpdatePostSerializer(data=request.data)

            if not serializer.is_valid():
                return self._handle_validation_errors(errors=serializer.errors)

            updated_post = PostService.update_post_by_id(post_id=post_id, user_id=request.user_id,
                                                         validated_data=serializer.validated_data)

            response_data = GetPostByIdResponse(data=updated_post)
            return Response(data=response_data.model_dump(mode='json'), status=status.HTTP_200_OK)
        except (PostNotFoundException, ValueError) as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_404_NOT_FOUND,
                message=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                        description=(
                            str(exception) if settings.DEBUG else ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id)),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_NOT_FOUND
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_404_NOT_FOUND
            )
        except PostUpdateForbidden as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message=ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED.format(post_id),
                        description=(str(exception) if settings.DEBUG else ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_403_FORBIDDEN,
            )
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request: Request, post_id: str):
        try:
            validate_post_id = validate_uuid(uuid_string=post_id)

            if not validate_post_id:
                raise ValueError(f'Post or space not found with id: {post_id}')

            post_deleted = PostService.delete_post_by_id(post_id=post_id, user_id=request.user_id)

            if not post_deleted:
                return Response(data=None, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except (PostNotFoundException, ValueError) as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_404_NOT_FOUND,
                message=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id),
                        description=(
                            str(exception) if settings.DEBUG else ApiErrors.POST_NOT_FOUND_WITH_ID.format(post_id)),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_NOT_FOUND
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_404_NOT_FOUND
            )
        except PostUpdateForbidden as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_403_FORBIDDEN,
                message=ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED.format(post_id),
                        description=(str(exception) if settings.DEBUG else ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_SPACE_UPDATE_NOT_ALLOWED
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_403_FORBIDDEN,
            )
        except PostAlreadyDeletedException as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_400_BAD_REQUEST,
                message=ApiErrors.POST_ALREADY_DELETED.format(post_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.POST_ALREADY_DELETED.format(post_id),
                        description=(str(exception) if settings.DEBUG else ApiErrors.POST_ALREADY_DELETED),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.POST_ALREADY_DELETED
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _handle_validation_errors(self, errors):
        formatted_errors = []

        for fields, messages in errors.items():
            formatted_errors.append(
                ApiErrorDetail(
                    source={ApiErrorSource.PARAMETER: fields},
                    title=ApiErrors.VALIDATION_ERROR,
                    description=str(messages)
                )
            )

        error_response = ApiErrorResponse(
            statusCode=400,
            message=ApiErrors.VALIDATION_ERROR,
            errors=formatted_errors
        )
        return Response(
            data=error_response.model_dump(mode='json', exclude_none=True),
            status=status.HTTP_400_BAD_REQUEST
        )


class ReminderView(APIView):
    def get(self, request: Request, space_id: uuid.UUID):
        try:
            validate_post_id = validate_uuid(uuid_string=str(space_id))

            if not validate_post_id:
                raise ValueError(f'Space not found {space_id}')

            post_dto = PostService.get_post_by_id(post_id=str(space_id))

            if not post_dto:
                raise ValueError(f'Space not found {space_id}')

            reminder_dto = ReminderService.get_reminder_by_space_id(space_id=str(space_id), user_id=request.user_id)
            response_data = GetReminderBySpaceIdResponse(data=reminder_dto)

            return Response(
                data=response_data.model_dump(mode='json'),
                status=status.HTTP_200_OK
            )
        except (ReminderNotFoundException, ValueError) as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_404_NOT_FOUND,
                message=ApiErrors.REMINDER_NOT_FOUND_WITH_ID.format(space_id),
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.REMINDER_NOT_FOUND_WITH_ID.format(space_id),
                        description=(
                            str(exception) if settings.DEBUG else ApiErrors.REMINDER_NOT_FOUND_WITH_ID.format(
                                space_id)),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.REMINDER_NOT_FOUND
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=(str(exception) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR),
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json', exclude_none=True),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request: Request, space_id: uuid.UUID):
        try:
            validate_post_id = validate_uuid(uuid_string=str(space_id))

            if not validate_post_id:
                raise ValueError(f'Space not found {space_id}')

            serializer = CreateReminderSerializer(data=request.data)

            if not serializer.is_valid():
                return self._handle_validation_error(serializer.errors)

            reminder_dto = CreateUpdateReminderDTO(**serializer.validated_data, space_id=space_id,
                                                   created_by=request.user_id)
            response_dto = ReminderService.create_or_update(dto=reminder_dto)
            return Response(data=response_dto.model_dump(mode='json'), status=status.HTTP_200_OK)
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
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
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
        return Response(data=error_response.model_dump(mode='json', exclude_none=True),
                        status=status.HTTP_400_BAD_REQUEST)
