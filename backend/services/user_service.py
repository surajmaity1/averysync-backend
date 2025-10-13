from backend.models.user import UserModel
from backend.constants.messages import ValidationErrors
from rest_framework.exceptions import ValidationError

class UserService:
    @classmethod
    def _validate_google_user_details(cls, google_user_details: dict) -> None:
        validation_errors = {}

        if not google_user_details.get('user_id'):
            validation_errors['user_id'] = ValidationErrors.GOOGLE_ID_REQUIRED
        if not google_user_details.get('email'):
            validation_errors['email'] = ValidationErrors.EMAIL_REQUIRED
        if not google_user_details.get('name'):
            validation_errors['name'] = ValidationErrors.NAME_REQUIRED
        if not google_user_details.get('image'):
            validation_errors['image'] = ValidationErrors.IMAGE_REQUIRED
        
        if validation_errors:
            raise ValidationError(validation_errors)




    @classmethod
    def create_or_update_user(cls, google_user_details: dict) -> UserModel:
        try:
            cls._validate_google_user_details(google_user_details)
            return User