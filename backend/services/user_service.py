from backend.models.user import UserModel
from backend.constants.follow import RelationshipStatus
from backend.constants.messages import ValidationErrors, RepositoryError
from rest_framework.exceptions import ValidationError
from backend.dto.follow_dto import RelationshipDTO
from backend.dto.profile_dto import ProfileDTO, UpdateProfileDTO
from backend.repositories.block_repository import BlockRepository
from backend.repositories.user_repositories import UserRepository
from backend.exceptions.auth_exceptions import UserNotFoundException, APIException
from backend.exceptions.follow_exception import UserBlockedException
from backend.services.follow_service import FollowService


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

    @classmethod
    def _prepare_profile_dto(
        cls, user: UserModel, relationship: RelationshipDTO
    ) -> ProfileDTO:
        return ProfileDTO(
            id=user.id,
            name=user.name,
            image=user.image,
            isPrivate=user.is_private,
            followerCount=user.follower_count,
            followingCount=user.following_count,
            relationship=relationship,
        )

    @classmethod
    def update_profile(cls, user_id: str, dto: UpdateProfileDTO) -> ProfileDTO:
        user = UserRepository.update_profile(user_id=user_id, is_private=dto.isPrivate)
        relationship = RelationshipDTO(status=RelationshipStatus.SELF, followsYou=False)
        return cls._prepare_profile_dto(user, relationship)

    @classmethod
    def get_profile(cls, viewer_id: str, target_user_id: str) -> ProfileDTO:
        if BlockRepository.is_blocked(viewer_id, target_user_id):
            raise UserBlockedException(target_user_id)

        user = UserRepository.get_by_id(target_user_id)
        relationship = FollowService.relationship_for(
            viewer_id=viewer_id, target_id=target_user_id
        )
        return cls._prepare_profile_dto(user, relationship)
