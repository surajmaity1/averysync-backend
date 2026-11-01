import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from django.test import SimpleTestCase, override_settings

from backend.dto.space_participant_dto import MuteParticipantDTO
from backend.exceptions.participant_exception import (
    ModerationForbiddenException,
    ParticipantNotFoundException,
    SelfMuteNotAllowedException,
    SpaceEndedException,
    SpaceNotLiveException,
)
from backend.exceptions.post_exception import SpaceNotFoundException
from backend.models.post import PostModel
from backend.models.space_participant import SpaceParticipantModel
from backend.models.space_participant_event import SpaceParticipantEventModel
from backend.services.space_participant_service import SpaceParticipantService

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
SCHEDULED_END = NOW + timedelta(hours=2)

HOST = SpaceParticipantModel.ParticipantRole.HOST
LISTENER = SpaceParticipantModel.ParticipantRole.LISTENER
ACTION = SpaceParticipantEventModel.ParticipantAction

SERVICE_PATH = "backend.services.space_participant_service"


def _space(created_by: str, **overrides) -> PostModel:
    defaults = {
        "id": uuid.uuid4(),
        "title": "BLR Meetup",
        "type": "SPACE",
        "status": PostModel.SpaceStatus.LIVE,
        "scheduled_ended_at": SCHEDULED_END,
        "created_by": created_by,
    }
    defaults.update(overrides)
    return PostModel(**defaults)


def _participant(space: PostModel, user_id: str, **overrides) -> SpaceParticipantModel:
    defaults = {
        "id": uuid.uuid4(),
        "post_id": space.id,
        "user_id": uuid.UUID(user_id),
        "role": LISTENER,
        "first_joined_at": NOW - timedelta(minutes=30),
        "last_joined_at": NOW - timedelta(minutes=30),
        "left_at": None,
        "is_muted": False,
        "muted_until": None,
        "created_by": user_id,
    }
    defaults.update(overrides)
    return SpaceParticipantModel(**defaults)


class SpaceParticipantServiceTestBase(SimpleTestCase):
    def setUp(self):
        self.host_id = str(uuid.uuid4())
        self.listener_id = str(uuid.uuid4())
        self.space = _space(created_by=self.host_id)
        self.space_id = str(self.space.id)

        patchers = {
            "get_post": patch(f"{SERVICE_PATH}.PostRepository.get_by_id"),
            "upsert_join": patch(
                f"{SERVICE_PATH}.SpaceParticipantRepository.upsert_join"
            ),
            "get_active": patch(
                f"{SERVICE_PATH}.SpaceParticipantRepository.get_active"
            ),
            "list_by_post": patch(
                f"{SERVICE_PATH}.SpaceParticipantRepository.list_by_post"
            ),
            "set_mute": patch(f"{SERVICE_PATH}.SpaceParticipantRepository.set_mute"),
            "clear_mute": patch(
                f"{SERVICE_PATH}.SpaceParticipantRepository.clear_mute"
            ),
            "mark_left": patch(f"{SERVICE_PATH}.SpaceParticipantRepository.mark_left"),
            "create_event": patch(
                f"{SERVICE_PATH}.SpaceParticipantEventRepository.create"
            ),
            "push_mute": patch("backend.utils.sfu.Sfu.push_mute"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        self.mocks["get_post"].return_value = self.space


@override_settings(
    STREAM_API_SECRET_KEY="test-secret",
    WEBRTC_ISSUER="backend-webrtc-issuer",
    WEBRTC_AUDIENCE="stream-go-service",
)
class SpaceParticipantServiceJoinTests(SpaceParticipantServiceTestBase):
    def _decode(self, token: str) -> dict:
        return jwt.decode(
            token,
            "test-secret",
            algorithms=["HS256"],
            audience="stream-go-service",
            options={"verify_exp": False},
        )

    def test_join_assigns_host_role_to_space_creator(self):
        participant = _participant(self.space, self.host_id, role=HOST)
        self.mocks["upsert_join"].return_value = (participant, True)

        response, created = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.host_id, now=NOW
        )

        self.assertTrue(created)
        self.mocks["upsert_join"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.host_id,
            role=HOST.value,
            joined_at=NOW,
        )
        self.assertEqual(response.data.role, "HOST")

    def test_join_assigns_listener_role_to_non_creator(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, True)

        response, created = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.mocks["upsert_join"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            role=LISTENER.value,
            joined_at=NOW,
        )
        self.assertEqual(response.data.role, "LISTENER")

    def test_join_maps_participant_model_to_camel_case_dto(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, True)

        response, _ = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        payload = response.model_dump(mode="json")["data"]
        self.assertEqual(payload["spaceId"], self.space_id)
        self.assertEqual(payload["userId"], self.listener_id)
        self.assertFalse(payload["isMuted"])
        self.assertIsNone(payload["mutedUntil"])
        self.assertIsNone(payload["leftAt"])
        self.assertIsNotNone(payload["firstJoinedAt"])
        self.assertIsNotNone(payload["lastJoinedAt"])

    def test_join_writes_join_event_with_self_as_actor(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, True)

        SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.listener_id,
            action=ACTION.JOIN.value,
        )

    def test_join_rejoin_returns_not_created(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, False)

        _, created = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.assertFalse(created)

    def test_join_token_carries_role_and_backward_compatible_claims(self):
        participant = _participant(self.space, self.host_id, role=HOST)
        self.mocks["upsert_join"].return_value = (participant, True)

        response, _ = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.host_id, now=NOW
        )

        claims = self._decode(response.token)
        self.assertEqual(claims["user_id"], self.host_id)
        self.assertEqual(claims["username"], self.host_id)
        self.assertEqual(claims["room_id"], self.space_id)
        self.assertEqual(claims["iss"], "backend-webrtc-issuer")
        self.assertEqual(claims["role"], "HOST")
        self.assertTrue(claims["is_host"])
        self.assertFalse(claims["is_muted"])
        self.assertIsNone(claims["muted_until"])
        self.assertEqual(claims["exp"], int(NOW.timestamp()) + 3600)

    def test_join_token_for_listener_keeps_is_host_false(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, True)

        response, _ = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        claims = self._decode(response.token)
        self.assertEqual(claims["role"], "LISTENER")
        self.assertFalse(claims["is_host"])

    def test_rejoin_while_muted_carries_mute_state_in_token_and_dto(self):
        muted_until = NOW + timedelta(minutes=20)
        participant = _participant(
            self.space,
            self.listener_id,
            is_muted=True,
            muted_until=muted_until,
            muted_by=self.host_id,
            muted_at=NOW - timedelta(minutes=10),
        )
        self.mocks["upsert_join"].return_value = (participant, False)

        response, _ = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.assertTrue(response.data.isMuted)
        self.assertEqual(response.data.mutedUntil, muted_until)
        claims = self._decode(response.token)
        self.assertTrue(claims["is_muted"])
        self.assertEqual(claims["muted_until"], int(muted_until.timestamp()))

    def test_join_lazily_expires_stale_mute_in_dto_and_token(self):
        for case, muted_until in [
            ("expired_before_now", NOW - timedelta(seconds=1)),
            ("expires_exactly_now", NOW),
        ]:
            with self.subTest(case=case):
                participant = _participant(
                    self.space,
                    self.listener_id,
                    is_muted=True,
                    muted_until=muted_until,
                )
                self.mocks["upsert_join"].return_value = (participant, False)

                response, _ = SpaceParticipantService.join(
                    space_id=self.space_id, user_id=self.listener_id, now=NOW
                )

                self.assertFalse(response.data.isMuted)
                self.assertIsNone(response.data.mutedUntil)
                claims = self._decode(response.token)
                self.assertFalse(claims["is_muted"])
                self.assertIsNone(claims["muted_until"])

    def test_join_permanent_mute_without_horizon_stays_muted(self):
        participant = _participant(
            self.space, self.listener_id, is_muted=True, muted_until=None
        )
        self.mocks["upsert_join"].return_value = (participant, False)

        response, _ = SpaceParticipantService.join(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.assertTrue(response.data.isMuted)
        self.assertIsNone(response.data.mutedUntil)
        claims = self._decode(response.token)
        self.assertTrue(claims["is_muted"])
        self.assertIsNone(claims["muted_until"])

    def test_join_scheduled_space_raises_not_live(self):
        self.space.status = PostModel.SpaceStatus.SCHEDULED

        with self.assertRaises(SpaceNotLiveException):
            SpaceParticipantService.join(
                space_id=self.space_id, user_id=self.listener_id, now=NOW
            )
        self.mocks["upsert_join"].assert_not_called()

    def test_join_ended_or_closed_space_raises_ended(self):
        for space_status in [
            PostModel.SpaceStatus.ENDED,
            PostModel.SpaceStatus.CLOSED,
        ]:
            with self.subTest(status=space_status.name):
                self.space.status = space_status

                with self.assertRaises(SpaceEndedException):
                    SpaceParticipantService.join(
                        space_id=self.space_id, user_id=self.listener_id, now=NOW
                    )

    def test_join_missing_space_raises_not_found(self):
        self.mocks["get_post"].side_effect = ValueError("Failed to fetch post")

        with self.assertRaises(SpaceNotFoundException):
            SpaceParticipantService.join(
                space_id=self.space_id, user_id=self.listener_id, now=NOW
            )

    def test_join_plain_post_raises_not_found(self):
        self.space.type = "POST"
        self.space.status = None

        with self.assertRaises(SpaceNotFoundException):
            SpaceParticipantService.join(
                space_id=self.space_id, user_id=self.listener_id, now=NOW
            )


class SpaceParticipantServiceEnsureActiveParticipantTests(
    SpaceParticipantServiceTestBase
):
    def test_ensure_creates_listener_row_for_non_creator(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, True)

        result = SpaceParticipantService.ensure_active_participant(
            space_id=self.space_id,
            user_id=self.listener_id,
            created_by=self.host_id,
            now=NOW,
        )

        self.mocks["upsert_join"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            role=LISTENER.value,
            joined_at=NOW,
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.listener_id,
            action=ACTION.JOIN.value,
        )
        self.assertEqual(result, participant)

    def test_ensure_creates_host_row_for_creator(self):
        participant = _participant(self.space, self.host_id, role=HOST)
        self.mocks["upsert_join"].return_value = (participant, True)

        SpaceParticipantService.ensure_active_participant(
            space_id=self.space_id,
            user_id=self.host_id,
            created_by=self.host_id,
            now=NOW,
        )

        self.mocks["upsert_join"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.host_id,
            role=HOST.value,
            joined_at=NOW,
        )

    def test_ensure_writes_no_join_event_on_rejoin(self):
        participant = _participant(self.space, self.listener_id)
        self.mocks["upsert_join"].return_value = (participant, False)

        SpaceParticipantService.ensure_active_participant(
            space_id=self.space_id,
            user_id=self.listener_id,
            created_by=self.host_id,
            now=NOW,
        )

        self.mocks["create_event"].assert_not_called()


class SpaceParticipantServiceGetParticipantsTests(SpaceParticipantServiceTestBase):
    def test_get_participants_maps_rows_with_effective_mute(self):
        active_muted = _participant(
            self.space,
            self.listener_id,
            is_muted=True,
            muted_until=NOW + timedelta(minutes=5),
        )
        expired_muted = _participant(
            self.space,
            self.host_id,
            role=HOST,
            is_muted=True,
            muted_until=NOW - timedelta(minutes=5),
        )
        self.mocks["list_by_post"].return_value = [active_muted, expired_muted]

        response = SpaceParticipantService.get_participants(
            space_id=self.space_id, now=NOW
        )

        self.assertEqual(len(response.data), 2)
        self.assertTrue(response.data[0].isMuted)
        self.assertEqual(response.data[0].mutedUntil, NOW + timedelta(minutes=5))
        self.assertFalse(response.data[1].isMuted)
        self.assertIsNone(response.data[1].mutedUntil)
        self.assertEqual(response.data[1].role, "HOST")

    def test_get_participants_passes_include_left_flag(self):
        self.mocks["list_by_post"].return_value = []

        response = SpaceParticipantService.get_participants(
            space_id=self.space_id, include_left=True, now=NOW
        )

        self.mocks["list_by_post"].assert_called_once_with(
            post_id=self.space_id, include_left=True
        )
        self.assertEqual(response.data, [])

    def test_get_participants_allows_scheduled_and_ended_spaces(self):
        self.mocks["list_by_post"].return_value = []
        for space_status in [
            PostModel.SpaceStatus.SCHEDULED,
            PostModel.SpaceStatus.ENDED,
            PostModel.SpaceStatus.CLOSED,
        ]:
            with self.subTest(status=space_status.name):
                self.space.status = space_status

                response = SpaceParticipantService.get_participants(
                    space_id=self.space_id, now=NOW
                )

                self.assertEqual(response.data, [])

    def test_get_participants_missing_space_raises_not_found(self):
        self.mocks["get_post"].side_effect = ValueError("Failed to fetch post")

        with self.assertRaises(SpaceNotFoundException):
            SpaceParticipantService.get_participants(space_id=self.space_id, now=NOW)


class SpaceParticipantServiceLeaveRemoveTests(SpaceParticipantServiceTestBase):
    def test_self_leave_marks_left_and_writes_leave_event(self):
        self.mocks["mark_left"].return_value = _participant(
            self.space, self.listener_id, left_at=NOW
        )

        SpaceParticipantService.leave_or_remove(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.listener_id,
            now=NOW,
        )

        self.mocks["mark_left"].assert_called_once_with(
            post_id=self.space_id, user_id=self.listener_id, left_at=NOW
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.listener_id,
            action=ACTION.LEAVE.value,
        )
        self.mocks["get_active"].assert_not_called()

    def test_host_removing_self_is_plain_leave(self):
        self.mocks["mark_left"].return_value = _participant(
            self.space, self.host_id, role=HOST, left_at=NOW
        )

        SpaceParticipantService.leave_or_remove(
            space_id=self.space_id,
            target_user_id=self.host_id,
            caller_id=self.host_id,
            now=NOW,
        )

        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.host_id,
            actor=self.host_id,
            action=ACTION.LEAVE.value,
        )

    def test_creator_removes_other_participant_without_participant_row(self):
        self.mocks["get_active"].return_value = None
        self.mocks["mark_left"].return_value = _participant(
            self.space, self.listener_id, left_at=NOW
        )

        SpaceParticipantService.leave_or_remove(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            now=NOW,
        )

        self.mocks["mark_left"].assert_called_once_with(
            post_id=self.space_id, user_id=self.listener_id, left_at=NOW
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.host_id,
            action=ACTION.REMOVE.value,
        )

    def test_role_based_host_removes_other_participant_with_remove_event(self):
        cohost_id = str(uuid.uuid4())
        self.mocks["get_active"].return_value = _participant(
            self.space, cohost_id, role=HOST
        )
        self.mocks["mark_left"].return_value = _participant(
            self.space, self.listener_id, left_at=NOW
        )

        SpaceParticipantService.leave_or_remove(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=cohost_id,
            now=NOW,
        )

        self.mocks["get_active"].assert_called_once_with(
            post_id=self.space_id, user_id=cohost_id
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=cohost_id,
            action=ACTION.REMOVE.value,
        )

    def test_non_host_removing_other_raises_forbidden(self):
        other_listener = str(uuid.uuid4())
        self.mocks["get_active"].return_value = _participant(
            self.space, self.listener_id
        )

        with self.assertRaises(ModerationForbiddenException):
            SpaceParticipantService.leave_or_remove(
                space_id=self.space_id,
                target_user_id=other_listener,
                caller_id=self.listener_id,
                now=NOW,
            )
        self.mocks["mark_left"].assert_not_called()

    def test_non_creator_not_in_space_removing_other_raises_forbidden(self):
        self.mocks["get_active"].return_value = None
        non_creator = str(uuid.uuid4())

        with self.assertRaises(ModerationForbiddenException):
            SpaceParticipantService.leave_or_remove(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=non_creator,
                now=NOW,
            )

    def test_leaving_when_not_active_raises_participant_not_found(self):
        self.mocks["mark_left"].return_value = None

        with self.assertRaises(ParticipantNotFoundException):
            SpaceParticipantService.leave_or_remove(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.listener_id,
                now=NOW,
            )
        self.mocks["create_event"].assert_not_called()

    def test_leave_scheduled_space_raises_not_live(self):
        self.space.status = PostModel.SpaceStatus.SCHEDULED

        with self.assertRaises(SpaceNotLiveException):
            SpaceParticipantService.leave_or_remove(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.listener_id,
                now=NOW,
            )

    def test_leave_ended_space_raises_ended(self):
        self.space.status = PostModel.SpaceStatus.ENDED

        with self.assertRaises(SpaceEndedException):
            SpaceParticipantService.leave_or_remove(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.listener_id,
                now=NOW,
            )


class SpaceParticipantServiceSetMuteStateTests(SpaceParticipantServiceTestBase):
    def _stub_host_and_target(self, **target_overrides):
        target = _participant(self.space, self.listener_id, **target_overrides)

        def get_active(post_id, user_id):
            if user_id == self.host_id:
                return _participant(self.space, self.host_id, role=HOST)
            if user_id == self.listener_id:
                return target
            return None

        self.mocks["get_active"].side_effect = get_active
        return target

    def test_temporary_mute_sets_horizon_and_writes_mute_event(self):
        self._stub_host_and_target()
        muted_until = NOW + timedelta(seconds=600)
        self.mocks["set_mute"].return_value = _participant(
            self.space,
            self.listener_id,
            is_muted=True,
            muted_until=muted_until,
            muted_by=self.host_id,
            muted_at=NOW,
        )

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(
                isMuted=True, durationSeconds=600, reason="background noise"
            ),
            now=NOW,
        )

        self.mocks["set_mute"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            muted_until=muted_until,
            muted_by=self.host_id,
            muted_at=NOW,
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.host_id,
            action=ACTION.MUTE.value,
            reason="background noise",
            muted_until=muted_until,
        )
        self.assertTrue(result.isMuted)
        self.assertEqual(result.mutedUntil, muted_until)

    def test_permanent_mute_anchors_to_scheduled_end(self):
        self._stub_host_and_target()
        self.mocks["set_mute"].return_value = _participant(
            self.space,
            self.listener_id,
            is_muted=True,
            muted_until=SCHEDULED_END,
        )

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=True),
            now=NOW,
        )

        self.mocks["set_mute"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            muted_until=SCHEDULED_END,
            muted_by=self.host_id,
            muted_at=NOW,
        )
        self.assertEqual(result.mutedUntil, SCHEDULED_END)

    def test_permanent_mute_without_scheduled_end_keeps_null_horizon(self):
        self.space.scheduled_ended_at = None
        self._stub_host_and_target()
        self.mocks["set_mute"].return_value = _participant(
            self.space, self.listener_id, is_muted=True, muted_until=None
        )

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=True),
            now=NOW,
        )

        self.mocks["set_mute"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            muted_until=None,
            muted_by=self.host_id,
            muted_at=NOW,
        )
        self.assertTrue(result.isMuted)
        self.assertIsNone(result.mutedUntil)

    def test_unmute_effectively_muted_clears_state_and_writes_unmute_event(self):
        self._stub_host_and_target(
            is_muted=True, muted_until=NOW + timedelta(minutes=10)
        )
        self.mocks["clear_mute"].return_value = _participant(
            self.space, self.listener_id
        )

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=False),
            now=NOW,
        )

        self.mocks["clear_mute"].assert_called_once_with(
            post_id=self.space_id, user_id=self.listener_id
        )
        self.mocks["create_event"].assert_called_once_with(
            post_id=self.space_id,
            target_user_id=self.listener_id,
            actor=self.host_id,
            action=ACTION.UNMUTE.value,
            reason=None,
            muted_until=None,
        )
        self.assertFalse(result.isMuted)

    def test_unmute_not_muted_participant_is_idempotent_without_event(self):
        for case, target_overrides in [
            ("never_muted", {}),
            (
                "lazily_expired_mute",
                {"is_muted": True, "muted_until": NOW - timedelta(minutes=1)},
            ),
        ]:
            with self.subTest(case=case):
                self.mocks["create_event"].reset_mock()
                self.mocks["clear_mute"].reset_mock()
                self._stub_host_and_target(**target_overrides)
                self.mocks["clear_mute"].return_value = _participant(
                    self.space, self.listener_id
                )

                result = SpaceParticipantService.set_mute_state(
                    space_id=self.space_id,
                    target_user_id=self.listener_id,
                    caller_id=self.host_id,
                    dto=MuteParticipantDTO(isMuted=False),
                    now=NOW,
                )

                self.mocks["clear_mute"].assert_called_once()
                self.mocks["create_event"].assert_not_called()
                self.assertFalse(result.isMuted)

    def test_creator_can_mute_without_participant_row(self):
        def get_active(post_id, user_id):
            if user_id == self.listener_id:
                return _participant(self.space, self.listener_id)
            return None

        self.mocks["get_active"].side_effect = get_active
        self.mocks["set_mute"].return_value = _participant(
            self.space, self.listener_id, is_muted=True, muted_until=SCHEDULED_END
        )

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=True),
            now=NOW,
        )

        self.assertTrue(result.isMuted)
        self.mocks["set_mute"].assert_called_once_with(
            post_id=self.space_id,
            user_id=self.listener_id,
            muted_until=SCHEDULED_END,
            muted_by=self.host_id,
            muted_at=NOW,
        )

    def test_mute_pushes_effective_state_to_sfu(self):
        self._stub_host_and_target()
        muted_until = NOW + timedelta(seconds=600)
        self.mocks["set_mute"].return_value = _participant(
            self.space,
            self.listener_id,
            is_muted=True,
            muted_until=muted_until,
            muted_by=self.host_id,
            muted_at=NOW,
        )

        SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=True, durationSeconds=600),
            now=NOW,
        )

        self.mocks["push_mute"].assert_called_once_with(
            space_id=self.space_id,
            user_id=self.listener_id,
            is_muted=True,
            muted_until=int(muted_until.timestamp()),
        )

    def test_unmute_pushes_cleared_state_to_sfu(self):
        self._stub_host_and_target(
            is_muted=True, muted_until=NOW + timedelta(minutes=10)
        )
        self.mocks["clear_mute"].return_value = _participant(
            self.space, self.listener_id
        )

        SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=False),
            now=NOW,
        )

        self.mocks["push_mute"].assert_called_once_with(
            space_id=self.space_id,
            user_id=self.listener_id,
            is_muted=False,
            muted_until=None,
        )

    def test_mute_succeeds_even_when_sfu_push_fails(self):
        self._stub_host_and_target()
        self.mocks["set_mute"].return_value = _participant(
            self.space, self.listener_id, is_muted=True, muted_until=SCHEDULED_END
        )
        self.mocks["push_mute"].side_effect = Exception("sfu unreachable")

        result = SpaceParticipantService.set_mute_state(
            space_id=self.space_id,
            target_user_id=self.listener_id,
            caller_id=self.host_id,
            dto=MuteParticipantDTO(isMuted=True),
            now=NOW,
        )

        self.assertTrue(result.isMuted)

    def test_self_mute_raises_before_host_check(self):
        with self.assertRaises(SelfMuteNotAllowedException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.host_id,
                caller_id=self.host_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )
        self.mocks["get_active"].assert_not_called()
        self.mocks["set_mute"].assert_not_called()

    def test_non_host_caller_raises_forbidden(self):
        self.mocks["get_active"].return_value = _participant(
            self.space, self.listener_id
        )
        other_listener = str(uuid.uuid4())

        with self.assertRaises(ModerationForbiddenException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=other_listener,
                caller_id=self.listener_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )
        self.mocks["set_mute"].assert_not_called()

    def test_non_creator_not_active_participant_raises_forbidden(self):
        self.mocks["get_active"].return_value = None
        non_creator = str(uuid.uuid4())

        with self.assertRaises(ModerationForbiddenException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=non_creator,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )

    def test_muting_inactive_target_raises_participant_not_found(self):
        def get_active(post_id, user_id):
            if user_id == self.host_id:
                return _participant(self.space, self.host_id, role=HOST)
            return None

        self.mocks["get_active"].side_effect = get_active

        with self.assertRaises(ParticipantNotFoundException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.host_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )
        self.mocks["set_mute"].assert_not_called()

    def test_target_leaving_during_mute_write_raises_participant_not_found(self):
        self._stub_host_and_target()
        self.mocks["set_mute"].return_value = None

        with self.assertRaises(ParticipantNotFoundException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.host_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )
        self.mocks["create_event"].assert_not_called()

    def test_mute_scheduled_space_raises_not_live(self):
        self.space.status = PostModel.SpaceStatus.SCHEDULED

        with self.assertRaises(SpaceNotLiveException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.host_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )

    def test_mute_ended_space_raises_ended(self):
        self.space.status = PostModel.SpaceStatus.CLOSED

        with self.assertRaises(SpaceEndedException):
            SpaceParticipantService.set_mute_state(
                space_id=self.space_id,
                target_user_id=self.listener_id,
                caller_id=self.host_id,
                dto=MuteParticipantDTO(isMuted=True),
                now=NOW,
            )


class SpaceParticipantServiceEffectiveMuteClaimsTests(SpaceParticipantServiceTestBase):
    """The connection token must carry each participant's *effective* mute so the
    SFU can enforce a host mute the moment a peer (re)connects. Without these
    claims the SFU reads is_muted=false on every join and un-silences a peer the
    host muted — everyone keeps hearing them.
    """

    def test_returns_false_none_when_no_active_participant(self):
        self.mocks["get_active"].return_value = None

        claims = SpaceParticipantService.effective_mute_claims(
            space_id=self.space_id, user_id=self.listener_id, now=NOW
        )

        self.assertEqual(claims, (False, None))

    def test_effective_mute_claims_reflect_participant_state(self):
        future = NOW + timedelta(minutes=10)
        past = NOW - timedelta(minutes=10)
        cases = [
            (
                "unmuted participant",
                {"is_muted": False, "muted_until": None},
                (False, None),
            ),
            (
                "permanent mute with no horizon",
                {"is_muted": True, "muted_until": None},
                (True, None),
            ),
            (
                "temporary mute with a future horizon",
                {"is_muted": True, "muted_until": future},
                (True, int(future.timestamp())),
            ),
            (
                "temporary mute past its horizon self-expires",
                {"is_muted": True, "muted_until": past},
                (False, None),
            ),
        ]
        for name, overrides, want in cases:
            with self.subTest(case=name):
                self.mocks["get_active"].return_value = _participant(
                    self.space, self.listener_id, **overrides
                )

                claims = SpaceParticipantService.effective_mute_claims(
                    space_id=self.space_id, user_id=self.listener_id, now=NOW
                )

                self.assertEqual(claims, want)
