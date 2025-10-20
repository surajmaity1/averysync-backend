from backend.models.user import UserModel
from backend_project.db.config import DBManager
from datetime import datetime, timezone
from django.db import transaction
import logging
from typing import Optional
from backend.exceptions.auth_exceptions import UserNotFoundException


logger = logging.getLogger(__name__)   


class UserRepository:
    @classmethod
    def _get_collection(cls):
        return DBManager().get_collection('users')


    @classmethod
    @transaction.atomic
    def create_or_update(cls, user_details: dict) -> UserModel:
        try:
            user_id = user_details.get('user_id')
            email = user_details.get('email')

            if not user_id or not email:
                raise ValueError('Both user_id and email are required.')

            user, created = UserModel.objects.update_or_create(
                user_id=user_id,
                defaults={
                    'user_id': user_id,
                    'email': email,
                    'name': user_details.get('name'),
                    'image': user_details.get('image'),
                    'sign_in_provider': 'GOOGLE',
                    'updated_at': datetime.now(timezone.utc),
                },
            )          
            logger.info(f'{'Created' if created else 'Updated'} user: {email}')
            return user

        except Exception as e:
            logger.error(f'Database error while creating/updating user: {e}')
            raise

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[UserModel]:
        try:
            return UserModel.objects.get(user_id=user_id)
        except Exception as exception:
            raise UserNotFoundException() from exception