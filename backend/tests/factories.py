import uuid
from datetime import datetime, timedelta, timezone

from backend.models.block import UserBlockModel
from backend.models.conversation import ConversationModel
from backend.models.conversation_member import ConversationMemberModel
from backend.models.follow import UserFollowModel
from backend.models.message import MessageModel
from backend.models.post import PostModel
from backend.models.post_like import PostLikeModel
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


def create_post(created_by: str, **overrides) -> PostModel:
    defaults = {
        "title": "Weekend plans",
        "type": "POST",
        "created_by": created_by,
    }
    defaults.update(overrides)
    return PostModel.objects.create(**defaults)


def create_post_like(post: PostModel, user: UserModel, **overrides) -> PostLikeModel:
    defaults = {
        "is_deleted": False,
        "created_by": str(user.id),
    }
    defaults.update(overrides)
    return PostLikeModel.objects.create(post=post, user=user, **defaults)


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


def create_follow(
    follower: UserModel, followee: UserModel, **overrides
) -> UserFollowModel:
    defaults = {
        "status": UserFollowModel.FollowStatus.ACCEPTED,
        "requested_at": NOW,
        "responded_at": NOW,
        "is_deleted": False,
        "created_by": str(follower.id),
    }
    defaults.update(overrides)
    return UserFollowModel.objects.create(
        follower=follower, followee=followee, **defaults
    )


def create_block(blocker: UserModel, blocked: UserModel, **overrides) -> UserBlockModel:
    defaults = {
        "is_deleted": False,
        "created_by": str(blocker.id),
    }
    defaults.update(overrides)
    return UserBlockModel.objects.create(blocker=blocker, blocked=blocked, **defaults)


def direct_dm_key(a, b) -> str:
    return ":".join(sorted([str(a), str(b)]))


def create_conversation(created_by: str, **overrides) -> ConversationModel:
    defaults = {
        "type": ConversationModel.ConversationType.DIRECT,
        "created_by": created_by,
    }
    defaults.update(overrides)
    return ConversationModel.objects.create(**defaults)


def create_member(
    conversation: ConversationModel, user: UserModel, **overrides
) -> ConversationMemberModel:
    defaults = {
        "role": ConversationMemberModel.MemberRole.MEMBER,
        "state": ConversationMemberModel.MemberState.ACCEPTED,
        "joined_at": NOW,
        "invited_by": str(user.id),
        "created_by": str(user.id),
    }
    defaults.update(overrides)
    return ConversationMemberModel.objects.create(
        conversation=conversation, user=user, **defaults
    )


def create_message(
    conversation: ConversationModel, sender: UserModel, **overrides
) -> MessageModel:
    defaults = {
        "type": MessageModel.MessageType.TEXT,
        "body": "hello there",
        "created_by": str(sender.id),
    }
    defaults.update(overrides)
    return MessageModel.objects.create(
        conversation=conversation, sender=sender, **defaults
    )
