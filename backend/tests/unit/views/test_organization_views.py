import json
import uuid
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import Resolver404, resolve, reverse
from rest_framework import status

from backend.constants.messages import ApiErrors, ApplicationMessages
from backend.constants.organization import OrganizationType
from backend.dto.responses.create_organization_response import (
    CreateOrganizationResponse,
)
from backend.dto.responses.get_organizations_response import (
    GetOrganizationsResponse,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
)
from backend.tests.fixtures.organization import (
    build_organization_dto,
    valid_create_organization_payload,
)
from backend.views.organization import OrganizationsView

SERVICE = "backend.views.organization.OrganizationService"


class OrganizationsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    def _post(self, body):
        request = self.factory.post(
            "/v1/organizations",
            data=json.dumps(body),
            content_type="application/json",
        )
        request.user_id = self.caller_id
        return OrganizationsView.as_view()(request)

    def _get(self):
        request = self.factory.get("/v1/organizations")
        request.user_id = self.caller_id
        return OrganizationsView.as_view()(request)

    @patch(f"{SERVICE}.create_organization")
    def test_create_organization_success_returns_201(self, mock_create):
        dto = build_organization_dto(caller_id=self.caller_id)
        mock_create.return_value = CreateOrganizationResponse(
            message=ApplicationMessages.ORGANIZATION_CREATED, data=dto
        )

        body = valid_create_organization_payload.copy()
        response = self._post(body)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["message"], ApplicationMessages.ORGANIZATION_CREATED
        )
        self.assertEqual(response.data["data"]["name"], "Tech University")
        self.assertEqual(response.data["data"]["shortName"], "tech-uni")
        self.assertEqual(response.data["data"]["type"], OrganizationType.COLLEGE.value)
        mock_create.assert_called_once()

    def test_validation_error_returns_400(self):
        body = {
            "shortName": "tech-uni",
            "type": 2,
        }
        response = self._post(body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], ApiErrors.VALIDATION_ERROR)
        self.assertIsInstance(response.data["errors"], list)

    @patch(f"{SERVICE}.create_organization")
    def test_duplicate_short_name_returns_409(self, mock_create):
        mock_create.side_effect = OrganizationAlreadyExistsException("tech-uni")

        body = {
            "name": "Tech University",
            "shortName": "tech-uni",
            "type": 2,
        }
        response = self._post(body)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("tech-uni", response.data["message"])

    @patch(f"{SERVICE}.create_organization")
    def test_unexpected_error_returns_500(self, mock_create):
        mock_create.side_effect = RuntimeError("database connection failed")

        body = {
            "name": "Tech University",
            "shortName": "tech-uni",
            "type": 2,
        }
        response = self._post(body)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], ApiErrors.UNEXPECTED_ERROR_OCCURRED)

    @patch(f"{SERVICE}.get_all_organizations")
    def test_get_all_organizations_success_returns_200(self, mock_get_all):
        dto1 = build_organization_dto(caller_id=self.caller_id, short_name="org-1")
        dto2 = build_organization_dto(caller_id=self.caller_id, short_name="org-2")
        mock_get_all.return_value = GetOrganizationsResponse(data=[dto1, dto2])

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["data"][0]["shortName"], "org-1")
        self.assertEqual(response.data["data"][1]["shortName"], "org-2")
        mock_get_all.assert_called_once()

    @patch(f"{SERVICE}.get_all_organizations")
    def test_get_all_organizations_empty_list_returns_200(self, mock_get_all):
        mock_get_all.return_value = GetOrganizationsResponse(data=[])

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"], [])
        mock_get_all.assert_called_once()

    @patch(f"{SERVICE}.get_all_organizations")
    def test_get_all_organizations_unexpected_error_returns_500(self, mock_get_all):
        mock_get_all.side_effect = RuntimeError("database failure")

        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], ApiErrors.UNEXPECTED_ERROR_OCCURRED)
        mock_get_all.assert_called_once()

    def test_url_resolves_under_v1_route(self):
        resolved = resolve("/v1/organizations")
        self.assertEqual(resolved.func.view_class, OrganizationsView)

    def test_root_organizations_does_not_resolve(self):
        with self.assertRaises(Resolver404):
            resolve("/organizations")

    def test_reverse_organizations(self):
        self.assertEqual(reverse("organizations"), "/v1/organizations")
