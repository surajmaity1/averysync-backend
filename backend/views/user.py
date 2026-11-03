from rest_framework.views import APIView
from rest_framework.request import Request
from backend.services.user_service import UserService
from rest_framework.response import Response
from rest_framework import status
from backend.constants.messages import ApiErrors
from backend.dto.profile_dto import UpdateProfileDTO
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail
from backend.serializers.update_profile_serializer import UpdateProfileSerializer
from backend.utils.uuid_validation import validate_uuid
from backend.views.follow import FollowErrorMixin
from django.conf import settings


class UsersView(FollowErrorMixin, APIView):
    def get(self, request: Request):
        try:
            profile = request.query_params.get("profile")

            if profile == "true":
                user_details = UserService.get_user_by_id(request.user_id)

                if not user_details:
                    return Response(
                        {
                            "statusCode": status.HTTP_404_NOT_FOUND,
                            "message": ApiErrors.USER_NOT_FOUND,
                            "data": None,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                response = {
                    "id": user_details.id,
                    "name": user_details.name,
                    # 'email': user_details.email,
                    "image": user_details.image,
                }

                return Response(
                    {
                        # 'message': 'success',
                        "data": response
                    },
                    status=status.HTTP_200_OK,
                )

            # TODO: Implement get all users & search functionaly

        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=ApiErrors.USER_DETAILS_FETCH_FAILED.format(
                            str(exception)
                        ),
                    )
                ]
                if settings.ERROR_DETAILS
                else ApiErrors.INTERNAL_SERVER_ERROR,
            )
            return Response(
                data=api_error_response.model_dump(mode="json"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def patch(self, request: Request):
        if request.query_params.get("profile") != "true":
            return self._error(
                status.HTTP_404_NOT_FOUND,
                ApiErrors.RESOURCE_NOT_FOUND,
                ValueError(ApiErrors.RESOURCE_NOT_FOUND),
            )

        serializer = UpdateProfileSerializer(data=request.data)

        if not serializer.is_valid():
            return self._validation_error(serializer.errors)

        try:
            dto = UserService.update_profile(
                user_id=request.user_id,
                dto=UpdateProfileDTO(**serializer.validated_data),
            )

            return Response(
                data={"data": dto.model_dump(mode="json")},
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)


class UserDetailView(FollowErrorMixin, APIView):
    def get(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            profile = UserService.get_profile(
                viewer_id=request.user_id, target_user_id=user_id
            )
            return Response(
                data={"data": profile.model_dump(mode="json")},
                status=status.HTTP_200_OK,
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)
