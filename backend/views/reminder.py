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

# class ReminderView(APIView):
#     def post(self, request: Request):
#         try:
#             serializer = CreateReminderSerializer(data=request.data)