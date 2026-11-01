from django.test import SimpleTestCase

from backend.constants.messages import ApiErrors
from backend.exceptions.follow_exception import (
    CannotBlockSelfException,
    CannotFollowSelfException,
    FollowerNotFoundException,
    FollowForbiddenException,
    FollowRequestNotFoundException,
    NotFollowingException,
    UserBlockedException,
)

FOLLOWER_ID = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"
USER_ID = "28cbefee-136e-4a33-b73e-8533599e5222"


class FollowExceptionTests(SimpleTestCase):
    def test_cannot_follow_self_uses_constant_message(self):
        exception = CannotFollowSelfException()

        self.assertEqual(str(exception), ApiErrors.CANNOT_FOLLOW_SELF)
        self.assertEqual(exception.message, ApiErrors.CANNOT_FOLLOW_SELF)

    def test_cannot_block_self_uses_constant_message(self):
        exception = CannotBlockSelfException()

        self.assertEqual(str(exception), ApiErrors.CANNOT_BLOCK_SELF)

    def test_follow_forbidden_uses_constant_message(self):
        exception = FollowForbiddenException(user_id=USER_ID)

        self.assertEqual(str(exception), ApiErrors.FOLLOW_LIST_FORBIDDEN)
        self.assertEqual(exception.user_id, USER_ID)

    def test_follow_request_not_found_formats_follower_id(self):
        exception = FollowRequestNotFoundException(follower_id=FOLLOWER_ID)

        self.assertEqual(
            str(exception), ApiErrors.FOLLOW_REQUEST_NOT_FOUND.format(FOLLOWER_ID)
        )

    def test_user_blocked_formats_user_id(self):
        exception = UserBlockedException(user_id=USER_ID)

        self.assertEqual(str(exception), ApiErrors.USER_BLOCKED.format(USER_ID))

    def test_not_following_formats_user_id(self):
        exception = NotFollowingException(user_id=USER_ID)

        self.assertEqual(str(exception), ApiErrors.NOT_FOLLOWING.format(USER_ID))

    def test_follower_not_found_formats_follower_id(self):
        exception = FollowerNotFoundException(follower_id=FOLLOWER_ID)

        self.assertEqual(
            str(exception), ApiErrors.FOLLOWER_NOT_FOUND.format(FOLLOWER_ID)
        )
