import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from backend.constants.messages import ApiErrors
from backend.dto.reminder_dto import CreateUpdateReminderDTO, ReminderDTO
from backend.dto.responses.error_response import ApiErrorResponse
from backend.services.reminder_service import ReminderService


def build_reminder_model(**overrides) -> MagicMock:
    """A stand-in ReminderModel. `post` is a related object exposing `.id`."""
    space_id = overrides.pop("space_id", uuid.uuid4())
    model = MagicMock()
    model.id = overrides.pop("id", uuid.uuid4())
    model.is_reminder_set = overrides.pop("is_reminder_set", True)
    model.post = MagicMock()
    model.post.id = space_id
    model.created_at = overrides.pop(
        "created_at", datetime(2026, 6, 6, 14, 9, 55, tzinfo=timezone.utc)
    )
    model.created_by = overrides.pop("created_by", "user-123")
    model.updated_at = overrides.pop(
        "updated_at", datetime(2026, 6, 9, 11, 31, 48, tzinfo=timezone.utc)
    )
    return model


class PrepareReminderDTOTests(TestCase):
    def test_maps_model_to_dto(self):
        space_id = uuid.uuid4()
        model = build_reminder_model(space_id=space_id, is_reminder_set=True)

        dto = ReminderService._prepare_post_dto(model)

        self.assertIsInstance(dto, ReminderDTO)
        self.assertEqual(dto.id, model.id)
        self.assertTrue(dto.isReminderSet)
        self.assertEqual(dto.spaceId, space_id)
        self.assertEqual(dto.createdAt, model.created_at)
        self.assertEqual(dto.createdBy, model.created_by)
        self.assertEqual(dto.updatedAt, model.updated_at)


class CreateOrUpdateTests(TestCase):
    def setUp(self):
        self.space_id = uuid.uuid4()
        self.user_id = "user-123"

    @patch("backend.services.reminder_service.ReminderRepository.create_or_update")
    def test_set_reminder_marks_not_deleted(self, mock_create_or_update):
        mock_create_or_update.return_value = build_reminder_model(
            space_id=self.space_id, is_reminder_set=True
        )
        dto = CreateUpdateReminderDTO(
            space_id=self.space_id, isReminderSet=True, created_by=self.user_id
        )

        result = ReminderService.create_or_update(dto)

        self.assertIsInstance(result, ReminderDTO)
        self.assertTrue(result.isReminderSet)
        passed_model = mock_create_or_update.call_args.kwargs["model"]
        self.assertFalse(passed_model.is_deleted)
        self.assertEqual(passed_model.is_reminder_set, True)
        self.assertEqual(str(passed_model.post_id), str(self.space_id))
        self.assertEqual(passed_model.created_by, self.user_id)

    @patch("backend.services.reminder_service.ReminderRepository.create_or_update")
    def test_unset_reminder_marks_deleted(self, mock_create_or_update):
        mock_create_or_update.return_value = build_reminder_model(
            space_id=self.space_id, is_reminder_set=False
        )
        dto = CreateUpdateReminderDTO(
            space_id=self.space_id, isReminderSet=False, created_by=self.user_id
        )

        ReminderService.create_or_update(dto)

        passed_model = mock_create_or_update.call_args.kwargs["model"]
        self.assertTrue(passed_model.is_deleted)

    @patch("backend.services.reminder_service.ReminderRepository.create_or_update")
    def test_repository_failure_wrapped_in_api_error_response(
        self, mock_create_or_update
    ):
        mock_create_or_update.side_effect = ValueError("db down")
        dto = CreateUpdateReminderDTO(
            space_id=self.space_id, isReminderSet=True, created_by=self.user_id
        )

        with self.assertRaises(ValueError) as ctx:
            ReminderService.create_or_update(dto)

        error = ctx.exception.args[0]
        self.assertIsInstance(error, ApiErrorResponse)
        self.assertEqual(error.statusCode, 500)
        self.assertEqual(error.message, ApiErrors.INTERNAL_SERVER_ERROR)


class GetReminderBySpaceIdTests(TestCase):
    def setUp(self):
        self.space_id = uuid.uuid4()
        self.user_id = "user-123"

    @patch("backend.services.reminder_service.ReminderRepository.get_by_id")
    def test_returns_dto_when_found(self, mock_get_by_id):
        mock_get_by_id.return_value = build_reminder_model(space_id=self.space_id)

        dto = ReminderService.get_reminder_by_space_id(
            space_id=str(self.space_id), user_id=self.user_id
        )

        self.assertIsInstance(dto, ReminderDTO)
        self.assertEqual(dto.spaceId, self.space_id)
        mock_get_by_id.assert_called_once_with(
            space_id=str(self.space_id), user_id=self.user_id
        )

    @patch("backend.services.reminder_service.ReminderRepository.get_by_id")
    def test_raises_value_error_when_not_found(self, mock_get_by_id):
        mock_get_by_id.return_value = None

        with self.assertRaises(ValueError) as ctx:
            ReminderService.get_reminder_by_space_id(
                space_id=str(self.space_id), user_id=self.user_id
            )

        self.assertIn(str(self.space_id), str(ctx.exception))

    @patch("backend.services.reminder_service.ReminderRepository.get_by_id")
    def test_repository_error_propagated_as_value_error(self, mock_get_by_id):
        mock_get_by_id.side_effect = ValueError("db down")

        with self.assertRaises(ValueError):
            ReminderService.get_reminder_by_space_id(
                space_id=str(self.space_id), user_id=self.user_id
            )


@override_settings(ERROR_DETAILS=False, DEBUG=False)
class CreateOrUpdateErrorWithoutDetailsTests(TestCase):
    @patch("backend.services.reminder_service.ReminderRepository.create_or_update")
    def test_error_uses_string_errors(self, mock_create_or_update):
        mock_create_or_update.side_effect = ValueError("db down")
        dto = CreateUpdateReminderDTO(
            space_id=uuid.uuid4(), isReminderSet=True, created_by="user"
        )

        with self.assertRaises(ValueError) as ctx:
            ReminderService.create_or_update(dto)

        error = ctx.exception.args[0]
        self.assertEqual(error.errors, ApiErrors.UNEXPECTED_ERROR_OCCURRED)
