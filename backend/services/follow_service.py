from datetime import datetime, timezone

from backend.constants.follow import RelationshipStatus
from backend.dto.follow_dto import FollowDTO, FollowUserDTO, RelationshipDTO
from backend.dto.responses.get_followers_response import GetFollowersResponse
from backend.dto.responses.get_following_response import GetFollowingResponse
from backend.dto.responses.get_follow_requests_response import (
    GetFollowRequestsResponse,
)
from backend.exceptions.follow_exception import (
    CannotFollowSelfException,
    FollowerNotFoundException,
    FollowForbiddenException,
    FollowRequestNotFoundException,
    NotFollowingException,
    UserBlockedException,
)
from backend.models.follow import UserFollowModel
from backend.repositories.block_repository import BlockRepository
from backend.repositories.follow_repository import FollowRepository
from backend.repositories.user_repositories import UserRepository

ACCEPTED = UserFollowModel.FollowStatus.ACCEPTED
PENDING = UserFollowModel.FollowStatus.PENDING


class FollowService:
    @classmethod
    def _prepare_follow_dto(cls, edge: UserFollowModel) -> FollowDTO:
        return FollowDTO(
            id=edge.id,
            followerId=edge.follower_id,
            followeeId=edge.followee_id,
            status=edge.status,
            requestedAt=edge.requested_at,
            respondedAt=edge.responded_at,
            createdAt=edge.created_at,
        )

    @classmethod
    def _prepare_follow_user_dto(cls, user, followed_at) -> FollowUserDTO:
        return FollowUserDTO(
            id=user.id,
            name=user.name,
            image=user.image,
            followedAt=followed_at,
        )

    @classmethod
    def follow(
        cls, follower_id: str, target_user_id: str, now: datetime | None = None
    ) -> tuple[FollowDTO, bool]:
        now = now or datetime.now(timezone.utc)
        if follower_id == target_user_id:
            raise CannotFollowSelfException()

        target = UserRepository.get_by_id(target_user_id)
        if BlockRepository.is_blocked(follower_id, target_user_id):
            raise UserBlockedException(target_user_id)

        target_status = PENDING if target.is_private else ACCEPTED
        responded_at = None if target.is_private else now

        edge, created = FollowRepository.create_or_reactivate(
            follower_id=follower_id,
            followee_id=target_user_id,
            target_status=target_status,
            requested_at=now,
            responded_at=responded_at,
        )
        return cls._prepare_follow_dto(edge), created

    @classmethod
    def unfollow_or_cancel(cls, follower_id: str, target_user_id: str) -> None:
        edge = FollowRepository.soft_delete(
            follower_id=follower_id, followee_id=target_user_id
        )
        if edge is None:
            raise NotFollowingException(target_user_id)
        return None

    @classmethod
    def accept(
        cls, followee_id: str, follower_id: str, now: datetime | None = None
    ) -> FollowDTO:
        now = now or datetime.now(timezone.utc)
        edge = FollowRepository.accept(
            follower_id=follower_id, followee_id=followee_id, responded_at=now
        )
        if edge is None:
            raise FollowRequestNotFoundException(follower_id)
        return cls._prepare_follow_dto(edge)

    @classmethod
    def reject(cls, followee_id: str, follower_id: str) -> None:
        edge = FollowRepository.soft_delete(
            follower_id=follower_id,
            followee_id=followee_id,
            expected_status=PENDING,
        )
        if edge is None:
            raise FollowRequestNotFoundException(follower_id)
        return None

    @classmethod
    def remove_follower(cls, followee_id: str, follower_id: str) -> None:
        edge = FollowRepository.soft_delete(
            follower_id=follower_id,
            followee_id=followee_id,
            expected_status=ACCEPTED,
        )
        if edge is None:
            raise FollowerNotFoundException(follower_id)
        return None

    @classmethod
    def _assert_list_visible(cls, viewer_id: str, target_user_id: str) -> None:
        if BlockRepository.is_blocked(viewer_id, target_user_id):
            raise UserBlockedException(target_user_id)

        target = UserRepository.get_by_id(target_user_id)
        if not target.is_private:
            return
        if viewer_id == target_user_id:
            return
        if FollowRepository.exists_accepted(
            follower_id=viewer_id, followee_id=target_user_id
        ):
            return
        raise FollowForbiddenException(target_user_id)

    @classmethod
    def get_followers(
        cls, viewer_id: str, target_user_id: str, limit: int, offset: int
    ) -> GetFollowersResponse:
        cls._assert_list_visible(viewer_id, target_user_id)
        edges, total = FollowRepository.list_followers(
            user_id=target_user_id, limit=limit, offset=offset
        )
        data = [
            cls._prepare_follow_user_dto(edge.follower, edge.responded_at)
            for edge in edges
        ]
        return GetFollowersResponse(data=data, total=total, limit=limit, offset=offset)

    @classmethod
    def get_following(
        cls, viewer_id: str, target_user_id: str, limit: int, offset: int
    ) -> GetFollowingResponse:
        cls._assert_list_visible(viewer_id, target_user_id)
        edges, total = FollowRepository.list_following(
            user_id=target_user_id, limit=limit, offset=offset
        )
        data = [
            cls._prepare_follow_user_dto(edge.followee, edge.responded_at)
            for edge in edges
        ]
        return GetFollowingResponse(data=data, total=total, limit=limit, offset=offset)

    @classmethod
    def get_requests(
        cls, user_id: str, limit: int, offset: int
    ) -> GetFollowRequestsResponse:
        edges, total = FollowRepository.list_pending(
            user_id=user_id, limit=limit, offset=offset
        )
        data = [
            cls._prepare_follow_user_dto(edge.follower, edge.requested_at)
            for edge in edges
        ]
        return GetFollowRequestsResponse(
            data=data, total=total, limit=limit, offset=offset
        )

    @classmethod
    def relationship_for(cls, viewer_id: str, target_id: str) -> RelationshipDTO:
        if viewer_id == target_id:
            return RelationshipDTO(status=RelationshipStatus.SELF, followsYou=False)

        edge = FollowRepository.get_edge(viewer_id, target_id)
        if edge is not None and not edge.is_deleted and edge.status == ACCEPTED:
            status = RelationshipStatus.FOLLOWING
        elif edge is not None and not edge.is_deleted and edge.status == PENDING:
            status = RelationshipStatus.PENDING
        else:
            status = RelationshipStatus.NONE

        follows_you = FollowRepository.exists_accepted(
            follower_id=target_id, followee_id=viewer_id
        )
        return RelationshipDTO(status=status, followsYou=follows_you)
