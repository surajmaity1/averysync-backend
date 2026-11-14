import uuid
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.constants.messages import ApplicationMessages
from backend.constants.organization import OrganizationType
from backend.dto.organization_dto import OrganizationDTO, UpdateOrganizationDTO
from backend.dto.responses.create_organization_response import (
    CreateOrganizationResponse,
)
from backend.dto.responses.get_organizations_response import (
    GetOrganizationsResponse,
)
from backend.dto.responses.update_organization_response import (
    UpdateOrganizationResponse,
)
from backend.exceptions.organization_exception import (
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateForbiddenException,
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

    @patch(
        "backend.services.organization_service.OrganizationRepository.get_by_short_name"
    )
    @patch("backend.services.organization_service.OrganizationRepository.update")
    @patch("backend.services.organization_service.OrganizationRepository.get_by_id")
    def test_update_organization_success(
        self, mock_get_by_id, mock_update, mock_get_by_sn
    ):
        mock_get_by_sn.return_value = None
        org_id = str(uuid.uuid4())
        caller_id = str(uuid.uuid4())

        existing_model = MagicMock(spec=OrganizationModel)
        existing_model.id = uuid.UUID(org_id)
        existing_model.name = "Old School"
        existing_model.short_name = "old-school"
        existing_model.description = "Old description"
        existing_model.type = OrganizationType.SCHOOL.value
        existing_model.created_by = caller_id
        existing_model.is_deleted = False
        mock_get_by_id.return_value = existing_model

        updated_model = MagicMock(spec=OrganizationModel)
        updated_model.id = uuid.UUID(org_id)
        updated_model.name = "Updated School"
        updated_model.short_name = "updated-school"
        updated_model.description = "Updated description"
        updated_model.type = OrganizationType.COLLEGE.value
        updated_model.created_by = caller_id
        updated_model.is_deleted = False
        mock_update.return_value = updated_model

        dto = UpdateOrganizationDTO(
            name="Updated School",
            shortName="updated-school",
            description="Updated description",
            type=OrganizationType.COLLEGE,
        )

        response = OrganizationService.update_organization(
            org_id=org_id,
            user_id=caller_id,
            dto=dto,
        )

        self.assertIsInstance(response, UpdateOrganizationResponse)
        self.assertEqual(response.message, ApplicationMessages.ORGANIZATION_UPDATED)
        self.assertEqual(response.data.name, "Updated School")
        self.assertEqual(response.data.shortName, "updated-school")
        self.assertEqual(response.data.type, OrganizationType.COLLEGE.value)
        mock_get_by_id.assert_called_once_with(org_id)
        mock_update.assert_called_once()

    @patch("backend.services.organization_service.OrganizationRepository.get_by_id")
    def test_update_organization_not_found_raises_exception(self, mock_get_by_id):
        mock_get_by_id.return_value = None
        org_id = str(uuid.uuid4())
        caller_id = str(uuid.uuid4())
        dto = UpdateOrganizationDTO(name="New Name")

        with self.assertRaises(OrganizationNotFoundException):
            OrganizationService.update_organization(
                org_id=org_id,
                user_id=caller_id,
                dto=dto,
            )

    @patch("backend.services.organization_service.OrganizationRepository.get_by_id")
    def test_update_organization_forbidden_for_non_creator(self, mock_get_by_id):
        org_id = str(uuid.uuid4())
        caller_id = str(uuid.uuid4())
        creator_id = str(uuid.uuid4())

        existing_model = MagicMock(spec=OrganizationModel)
        existing_model.id = uuid.UUID(org_id)
        existing_model.created_by = creator_id
        existing_model.is_deleted = False
        mock_get_by_id.return_value = existing_model

        dto = UpdateOrganizationDTO(name="New Name")

        with self.assertRaises(OrganizationUpdateForbiddenException):
            OrganizationService.update_organization(
                org_id=org_id,
                user_id=caller_id,
                dto=dto,
            )

    @patch(
        "backend.services.organization_service.OrganizationRepository.get_by_short_name"
    )
    @patch("backend.services.organization_service.OrganizationRepository.get_by_id")
    def test_update_organization_duplicate_short_name_raises_conflict(
        self, mock_get_by_id, mock_get_by_sn
    ):
        org_id = str(uuid.uuid4())
        caller_id = str(uuid.uuid4())

        existing_model = MagicMock(spec=OrganizationModel)
        existing_model.id = uuid.UUID(org_id)
        existing_model.short_name = "current-sn"
        existing_model.created_by = caller_id
        existing_model.is_deleted = False
        mock_get_by_id.return_value = existing_model

        other_model = MagicMock(spec=OrganizationModel)
        other_model.id = uuid.uuid4()
        other_model.short_name = "taken-sn"
        mock_get_by_sn.return_value = other_model

        dto = UpdateOrganizationDTO(shortName="taken-sn")

        with self.assertRaises(OrganizationAlreadyExistsException):
            OrganizationService.update_organization(
                org_id=org_id,
                user_id=caller_id,
                dto=dto,
            )
