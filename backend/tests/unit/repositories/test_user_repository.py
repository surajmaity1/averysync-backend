from django.test import TestCase

from backend.constants.messages import RepositoryError
from backend.models.user import UserModel
from backend.repositories.user_repositories import UserRepository
from backend.tests.factories import create_user


class UserRepositoryUpdateProfileTests(TestCase):
    def test_update_profile_sets_is_private_true(self):
        user = create_user(is_private=False)

        updated = UserRepository.update_profile(user_id=str(user.id), is_private=True)

        self.assertTrue(updated.is_private)
        self.assertTrue(UserModel.objects.get(id=user.id).is_private)

    def test_update_profile_sets_is_private_false(self):
        user = create_user(is_private=True)

        updated = UserRepository.update_profile(user_id=str(user.id), is_private=False)

        self.assertFalse(updated.is_private)

    def test_update_profile_bad_uuid_translates_to_repository_error(self):
        with self.assertRaises(ValueError) as ctx:
            UserRepository.update_profile(user_id="not-a-uuid", is_private=True)

        self.assertIn(
            RepositoryError.PROFILE_UPDATE_FAILED.format(""), str(ctx.exception)
        )
