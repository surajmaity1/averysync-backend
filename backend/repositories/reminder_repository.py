from backend.constants.messages import RepositoryError
from backend.models.reminder import ReminderModel
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class ReminderRepository:
    @classmethod
    @transaction.atomic
    def create_or_update(cls, model: ReminderModel) -> ReminderModel:
        try:
            reminder_details_data = {
                'is_reminder_set': model.is_reminder_set,
                'is_deleted': model.is_deleted,
                'updated_at': model.updated_at,
                'created_by': model.created_by,
            }
            created_or_updated_reminder, created = ReminderModel.objects.update_or_create(
                user_id=model.user_id,
                post_id=model.post_id,
                defaults=reminder_details_data
            )

            if created:
                logger.info(f'Reminder created with id: {created_or_updated_reminder.id}')
            else:
                logger.info(f'Reminder updated with id: {created_or_updated_reminder.id}')
            return created_or_updated_reminder
        except Exception as e:
            logger.error(f'Failed to create or update reminder: {str(e)}')
            raise ValueError(RepositoryError.REMINDER_CREATE_UPDATE_FAILED.format(str(e)))

    @classmethod
    @transaction.atomic
    def get_by_id(cls, space_id: str, user_id: str) -> ReminderModel | None:
        try:
            reminder = ReminderModel.objects.get(post_id=space_id, user_id=user_id)
            return reminder
        except Exception as exception:
            logger.error(f'Failed to fetch reminder: {str(exception)}')
            raise ValueError(RepositoryError.REMINDER_FETCH_FAILED.format(str(exception)))
