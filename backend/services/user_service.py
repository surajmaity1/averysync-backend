from backend.models.user import UserModel
from backend.constants.messages import ValidationErrors, RepositoryError
from rest_framework.exceptions import ValidationError
from backend.repositories.user_repositories import UserRepository
from backend.exceptions.auth_exceptions import UserNotFoundException, APIException


class UserService:
    @classmethod
    def _validate_google_user_details(cls, google_user_details: dict) -> None:
        validation_errors = {}

        if not google_user_details.get("user_id"):
            validation_errors["user_id"] = ValidationErrors.GOOGLE_ID_REQUIRED
        if not google_user_details.get("email"):
            validation_errors["email"] = ValidationErrors.EMAIL_REQUIRED
        if not google_user_details.get("name"):
            validation_errors["name"] = ValidationErrors.NAME_REQUIRED
        if not google_user_details.get("image"):
            validation_errors["image"] = ValidationErrors.IMAGE_REQUIRED

        if validation_errors:
            raise ValidationError(validation_errors)

    @classmethod
    def create_or_update_user(cls, google_user_details: dict) -> UserModel:
        try:
            cls._validate_google_user_details(google_user_details)
            return UserRepository.create_or_update(google_user_details)
        except (UserNotFoundException, APIException, ValidationError):
            raise
        except Exception as exception:
            raise APIException(
                RepositoryError.USER_CREATE_UPDATE_FAILED.format(str(exception))
            ) from exception

    @classmethod
    def get_user_by_id(cls, user_id: str) -> UserModel:
        try:
            user = UserRepository.get_by_id(user_id)

            if not user:
                raise UserNotFoundException()

            return user
        except Exception as exception:
            raise APIException(
                RepositoryError.USER_NOT_FOUND.format(str(exception))
            ) from exception
