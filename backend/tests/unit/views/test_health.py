from rest_framework.test import APISimpleTestCase, APIClient
from unittest.mock import patch
from rest_framework.reverse import reverse
from rest_framework import status


class HealthAPITests(APISimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    @patch(
        target="backend_project.db.config.DBManager.check_db_health", return_value=True
    )
    def test_health_api_returns_200_when_db_healthy(self, mocked):
        url = reverse("health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["application"], {"status": "UP"})
        self.assertEqual(response.data["database"], {"status": "UP"})
