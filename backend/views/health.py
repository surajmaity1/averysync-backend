from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.response import Response
from backend.constants.health import AppHealthStatus, ComponentHealthStatus


class HealthView(APIView):
    @extend_schema(
        operation_id='health_check',
        summary='Health check',
        description='Check health of the backend app',
        tags=['health'],
        responses={
            200: OpenApiResponse(description='App is healthy'),
            503: OpenApiResponse(description='App is not healthy')
        }
    )
    def get(self, request):
        db_status = ComponentHealthStatus.UP.name
        overall_status = AppHealthStatus.UP
        
        response = {
            'status': overall_status.name,
            'components': {
                'db': {
                    'status': db_status
                },
            }
        }
        return Response(response, overall_status.http_status)