from unittest import TestCase
from unittest.mock import patch, sentinel

from rest_framework.exceptions import ValidationError

from backend.constants.messages import ValidationErrors
from backend.exceptions.auth_exceptions import APIException, UserNotFoundException
from backend.services.user_service import UserService


def valid_google_details(**overrides) -> dict:
    details = {
        "user_id": "google-oauth2|123",
        "email": "user@example.com",
        "name": "Test User",
        "image": "https://example.com/avatar.png",
    }
    details.update(overrides)
    return details


class ValidateGoogleUserDetailsTests(TestCase):
    def test_valid_details_pass(self):
        # Should not raise.
        self.assertIsNone(
            UserService._validate_google_user_details(valid_google_details())
        )

    def test_missing_user_id_raises_validation_error(self):
        details = valid_google_details(user_id="")

        with self.assertRaises(ValidationError) as ctx:
            UserService._validate_google_user_details(details)

        self.assertIn("user_id", ctx.exception.detail)
        self.assertIn(
            ValidationErrors.GOOGLE_ID_REQUIRED,
            str(ctx.exception.detail["user_id"]),
        )

    def test_missing_email_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            UserService._validate_google_user_details(valid_google_details(email=""))

        self.assertIn("email", ctx.exception.detail)

    def test_missing_name_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            UserService._validate_google_user_details(valid_google_details(name=""))

        self.assertIn("name", ctx.exception.detail)

    def test_missing_image_raises_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            UserService._validate_google_user_details(valid_google_details(image=""))

        self.assertIn("image", ctx.exception.detail)

    def test_all_missing_collected_together(self):
        with self.assertRaises(ValidationError) as ctx:
            UserService._validate_google_user_details({})

        self.assertEqual(
            set(ctx.exception.detail.keys()),
            {"user_id", "email", "name", "image"},
        )


class CreateOrUpdateUserTests(TestCase):
    @patch("backend.services.user_service.UserRepository.create_or_update")
    def test_creates_user_with_valid_details(self, mock_create_or_update):
        mock_create_or_update.return_value = sentinel.user
        details = valid_google_details()

        result = UserService.create_or_update_user(details)

        self.assertIs(result, sentinel.user)
        mock_create_or_update.assert_called_once_with(details)

    @patch("backend.services.user_service.UserRepository.create_or_update")
    def test_validation_error_propagates(self, mock_create_or_update):
        with self.assertRaises(ValidationError):
            UserService.create_or_update_user(valid_google_details(email=""))

        mock_create_or_update.assert_not_called()

    @patch("backend.services.user_service.UserRepository.create_or_update")
    def test_known_auth_exceptions_propagate_unchanged(self, mock_create_or_update):
        mock_create_or_update.side_effect = UserNotFoundException()

        with self.assertRaises(UserNotFoundException):
            UserService.create_or_update_user(valid_google_details())

    @patch("backend.services.user_service.UserRepository.create_or_update")
    def test_unexpected_error_wrapped_in_api_exception(self, mock_create_or_update):
        mock_create_or_update.side_effect = RuntimeError("db down")

        with self.assertRaises(APIException) as ctx:
            UserService.create_or_update_user(valid_google_details())

        self.assertIn("db down", str(ctx.exception))


class GetUserByIdTests(TestCase):
    @patch("backend.services.user_service.UserRepository.get_by_id")
    def test_returns_user_when_found(self, mock_get_by_id):
        mock_get_by_id.return_value = sentinel.user

        result = UserService.get_user_by_id("user-1")

        self.assertIs(result, sentinel.user)
        mock_get_by_id.assert_called_once_with("user-1")

    @patch("backend.services.user_service.UserRepository.get_by_id")
    def test_none_result_raises_api_exception(self, mock_get_by_id):
        mock_get_by_id.return_value = None

        with self.assertRaises(APIException):
            UserService.get_user_by_id("missing")

    @patch("backend.services.user_service.UserRepository.get_by_id")
    def test_repository_error_wrapped_in_api_exception(self, mock_get_by_id):
        mock_get_by_id.side_effect = UserNotFoundException()

        with self.assertRaises(APIException):
            UserService.get_user_by_id("user-1")
