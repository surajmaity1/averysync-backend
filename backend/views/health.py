from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.response import Response
from backend.constants.health import AppHealthStatus, ComponentHealthStatus
from backend_project.db.config import DBManager


db_manager = DBManager()


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
        global db_manager
        
        db_status = ComponentHealthStatus.UP.name if db_manager.check_db_health() else ComponentHealthStatus.DOWN.name
        overall_status = AppHealthStatus.UP

        response = {
            'application': {
                'status': overall_status.name,
            },
            'database': {
                'status': db_status,
            },
        }
        
        return Response(response, overall_status.http_status)