from rest_framework.views import APIView
from rest_framework.request import Request
from backend.services.user_service import UserService
from rest_framework.response import Response
from rest_framework import status
from backend.constants.messages import ApiErrors
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail
from django.conf import settings


class UsersView(APIView):
    def get(self, request: Request):
        try:
            profile = request.query_params.get('profile')

            if profile == 'true':
                user_details = UserService.get_user_by_id(request.user_id)
                                
                if not user_details:
                    return Response(
                        {
                        'statusCode': status.HTTP_404_NOT_FOUND,
                        'message': ApiErrors.USER_NOT_FOUND,
                        'data': None,
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                response = {
                    'id': user_details.id,
                    'name': user_details.name,
                    # 'email': user_details.email,
                    'image': user_details.image,
                }
                
                return Response({
                    # 'message': 'success',
                    'data': response
                },status=status.HTTP_200_OK)
            
            # TODO: Implement get all users & search functionaly
            
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=ApiErrors.USER_DETAILS_FETCH_FAILED.format(str(exception))
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(APIView):
    def get(self, request: Request, user_id: str):
        try:            
            user_details = UserService.get_user_by_id(user_id)
            if not user_details:
                return Response(
                    {
                        'statusCode': status.HTTP_404_NOT_FOUND,
                        'message': ApiErrors.USER_NOT_FOUND,
                        'data': None,
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            response = {
                'name': user_details.name,
                'image': user_details.image,
            }
            
            return Response({
                'data': response
            },status=status.HTTP_200_OK)
            
        except Exception as exception:
            api_error_response = ApiErrorResponse(
                statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                        description=ApiErrors.USER_DETAILS_FETCH_FAILED.format(str(exception))
                    )
                ] if settings.ERROR_DETAILS else ApiErrors.INTERNAL_SERVER_ERROR
            )
            return Response(
                data=api_error_response.model_dump(mode='json'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
