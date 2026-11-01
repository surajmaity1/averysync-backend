import uuid
from datetime import datetime, timedelta, timezone

from backend.models.post import PostModel
from backend.models.space_participant import SpaceParticipantModel
from backend.models.user import UserModel

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)


def create_user(**overrides) -> UserModel:
    suffix = uuid.uuid4().hex[:12]
    defaults = {
        "user_id": f"google-{suffix}",
        "email": f"user-{suffix}@example.com",
        "name": "Test User",
        "sign_in_provider": "google",
    }
    defaults.update(overrides)
    return UserModel.objects.create(**defaults)


def create_space(created_by: str, **overrides) -> PostModel:
    defaults = {
        "title": "BLR Meetup",
        "type": "SPACE",
        "status": PostModel.SpaceStatus.LIVE,
        "scheduled_ended_at": NOW + timedelta(hours=2),
        "created_by": created_by,
    }
    defaults.update(overrides)
    return PostModel.objects.create(**defaults)


def create_participant(
    post: PostModel, user: UserModel, **overrides
) -> SpaceParticipantModel:
    defaults = {
        "role": SpaceParticipantModel.ParticipantRole.LISTENER,
        "first_joined_at": NOW,
        "last_joined_at": NOW,
        "created_by": str(user.id),
    }
    defaults.update(overrides)
    return SpaceParticipantModel.objects.create(post=post, user=user, **defaults)
