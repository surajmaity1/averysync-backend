from backend.models.user import UserModel


class UserRepository:
    @classmethod
    def create_or_update(cls, user_details: dict) -> UserModel:
        try:
            