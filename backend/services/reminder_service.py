from datetime import datetime, timezone

from django.conf import settings
from rest_framework import status

from backend.constants.messages import ApiErrors
from backend.dto.reminder_dto import CreateUpdateReminderDTO, ReminderDTO
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail, ApiErrorSource
from backend.models.reminder import ReminderModel
from backend.repositories.reminder_repository import ReminderRepository
from backend.exceptions.reminder_exception import ReminderNotFoundException


class ReminderService:
    @classmethod
    def _prepare_post_dto(cls, model: ReminderModel) -> ReminderDTO:
        return ReminderDTO(
            id=model.id,
            isReminderSet=model.is_reminder_set,
            spaceId=model.post.id,
            createdAt=model.created_at,
            createdBy=model.created_by,
            updatedAt=model.updated_at
        )

    @classmethod
    def create_or_update(cls, dto: CreateUpdateReminderDTO):
        try:
            reminder_model = ReminderModel(
                user_id=dto.created_by,
                post_id=dto.space_id,
                is_reminder_set=dto.isReminderSet,
                is_deleted=False if dto.isReminderSet else True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=dto.created_by,
            )
            created_or_updated_reminder = ReminderRepository.create_or_update(model=reminder_model)
            
            return cls._prepare_post_dto(created_or_updated_reminder)
        except Exception as e:
            raise ValueError(
                ApiErrorResponse(
                    statusCode=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=ApiErrors.INTERNAL_SERVER_ERROR,
                    errors=[
                        ApiErrorDetail(
                            source={ApiErrorSource.PARAMETER: 'server'},
                            title=ApiErrors.UNEXPECTED_ERROR_OCCURRED,
                            description=(str(e) if settings.DEBUG else ApiErrors.INTERNAL_SERVER_ERROR)
                        )
                    ] if settings.ERROR_DETAILS else ApiErrors.UNEXPECTED_ERROR_OCCURRED
                )
            )

    @classmethod
    def get_reminder_by_space_id(cls, space_id: str) -> ReminderDTO:
        try:
            reminder_model = ReminderRepository.get_by_id(space_id=space_id)
            
            if not reminder_model:
                raise ReminderNotFoundException(space_id=space_id)
            
            return cls._prepare_post_dto(model=reminder_model)
        except Exception as exception:
            raise ValueError(f'Reminder with space id {space_id} not found: {str(exception)}')
