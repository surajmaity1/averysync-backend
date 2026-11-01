from django.test import SimpleTestCase

from backend.constants.messages import ApiErrors
from backend.exceptions.participant_exception import (
    ModerationForbiddenException,
    ParticipantNotFoundException,
    SelfMuteNotAllowedException,
    SpaceEndedException,
    SpaceNotLiveException,
)

SPACE_ID = "28cbefee-136e-4a33-b73e-8533599e5222"
USER_ID = "9dee2457-9d0b-4bd8-a509-abaaaf618cfa"


class ParticipantExceptionTests(SimpleTestCase):
    def test_participant_not_found_formats_user_and_space_id(self):
        exception = ParticipantNotFoundException(user_id=USER_ID, space_id=SPACE_ID)

        self.assertEqual(
            str(exception),
            ApiErrors.PARTICIPANT_NOT_FOUND_WITH_ID.format(USER_ID, SPACE_ID),
        )

    def test_moderation_forbidden_formats_space_id(self):
        exception = ModerationForbiddenException(space_id=SPACE_ID)

        self.assertEqual(
            str(exception), ApiErrors.MODERATION_NOT_ALLOWED.format(SPACE_ID)
        )

    def test_space_not_live_formats_space_id(self):
        exception = SpaceNotLiveException(space_id=SPACE_ID)

        self.assertEqual(str(exception), ApiErrors.SPACE_NOT_LIVE.format(SPACE_ID))

    def test_space_ended_formats_space_id(self):
        exception = SpaceEndedException(space_id=SPACE_ID)

        self.assertEqual(str(exception), ApiErrors.SPACE_ALREADY_ENDED.format(SPACE_ID))

    def test_self_mute_not_allowed_uses_constant_message(self):
        exception = SelfMuteNotAllowedException()

        self.assertEqual(str(exception), ApiErrors.SELF_MUTE_NOT_ALLOWED)
