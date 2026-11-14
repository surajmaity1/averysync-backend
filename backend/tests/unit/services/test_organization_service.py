import uuid
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.constants.messages import ApplicationMessages
from backend.constants.organization import OrganizationType
from backend.dto.organization_dto import OrganizationDTO
from backend.dto.responses.create_organization_response import (
    CreateOrganizationResponse,
)
from backend.dto.responses.get_organizations_response import (
    GetOrganizationsResponse,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
)
from backend.models.organization import OrganizationModel
from backend.services.organization_service import OrganizationService
from backend.tests.fixtures.organization import build_create_organization_dto


class OrganizationServiceTests(SimpleTestCase):
    @patch("backend.services.organization_service.OrganizationRepository.create")
    @patch(
        "backend.services.organization_service.OrganizationRepository.get_by_short_name"
    )
    def test_create_organization_success(self, mock_get_by_sn, mock_create):
        mock_get_by_sn.return_value = None
        caller_id = str(uuid.uuid4())
        mock_model = MagicMock(spec=OrganizationModel)
        mock_model.id = uuid.uuid4()
        mock_model.name = "Apex Institute"
        mock_model.short_name = "apex-inst"
        mock_model.description = "Coaching institute"
        mock_model.type = OrganizationType.PRIVATE_TUITION.value
        mock_model.is_deleted = False
        mock_model.created_at = MagicMock()
        mock_model.updated_at = None
        mock_model.created_by = caller_id
        mock_model.updated_by = None
        mock_create.return_value = mock_model

        dto = build_create_organization_dto(caller_id=caller_id)

        response: CreateOrganizationResponse = OrganizationService.create_organization(
            dto
        )

        self.assertIsInstance(response, CreateOrganizationResponse)
        self.assertEqual(response.message, ApplicationMessages.ORGANIZATION_CREATED)
        self.assertIsInstance(response.data, OrganizationDTO)
        self.assertEqual(response.data.id, mock_model.id)
        self.assertEqual(response.data.name, "Apex Institute")
        self.assertEqual(response.data.shortName, "apex-inst")
        self.assertEqual(response.data.type, OrganizationType.PRIVATE_TUITION.value)
        self.assertEqual(response.data.createdBy, caller_id)
        mock_create.assert_called_once()

    @patch(
        "backend.services.organization_service.OrganizationRepository.get_by_short_name"
    )
    def test_create_organization_duplicate_short_name_raises_exception(
        self, mock_get_by_sn
    ):
        mock_get_by_sn.return_value = MagicMock(spec=OrganizationModel)
        caller_id = str(uuid.uuid4())

        dto = build_create_organization_dto(
            caller_id=caller_id,
            name="Duplicate School",
            short_name="dup-school",
            org_type=OrganizationType.SCHOOL,
        )

        with self.assertRaises(OrganizationAlreadyExistsException) as ctx:
            OrganizationService.create_organization(dto)

        self.assertIn("dup-school", str(ctx.exception))

    @patch("backend.services.organization_service.OrganizationRepository.get_all")
    def test_get_all_organizations_success(self, mock_get_all):
        caller_id = str(uuid.uuid4())
        model1 = MagicMock(spec=OrganizationModel)
        model1.id = uuid.uuid4()
        model1.name = "Apex Institute"
        model1.short_name = "apex-inst"
        model1.description = "Coaching institute"
        model1.type = OrganizationType.PRIVATE_TUITION.value
        model1.created_by = caller_id

        model2 = MagicMock(spec=OrganizationModel)
        model2.id = uuid.uuid4()
        model2.name = "Tech University"
        model2.short_name = "tech-uni"
        model2.description = "Engineering college"
        model2.type = OrganizationType.COLLEGE.value
        model2.created_by = caller_id

        mock_get_all.return_value = [model1, model2]

        response = OrganizationService.get_all_organizations()

        self.assertIsInstance(response, GetOrganizationsResponse)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0].id, model1.id)
        self.assertEqual(response.data[0].name, "Apex Institute")
        self.assertEqual(response.data[0].shortName, "apex-inst")
        self.assertEqual(response.data[0].type, OrganizationType.PRIVATE_TUITION.value)
        self.assertEqual(response.data[0].createdBy, caller_id)

        self.assertEqual(response.data[1].id, model2.id)
        self.assertEqual(response.data[1].name, "Tech University")
        self.assertEqual(response.data[1].shortName, "tech-uni")
        self.assertEqual(response.data[1].type, OrganizationType.COLLEGE.value)
        self.assertEqual(response.data[1].createdBy, caller_id)
        mock_get_all.assert_called_once()

    @patch("backend.services.organization_service.OrganizationRepository.get_all")
    def test_get_all_organizations_empty(self, mock_get_all):
        mock_get_all.return_value = []

        response = OrganizationService.get_all_organizations()

        self.assertIsInstance(response, GetOrganizationsResponse)
        self.assertEqual(response.data, [])
        mock_get_all.assert_called_once()
