from datetime import datetime, timezone

from backend.dto.post_like_dto import LikeStateDTO
from backend.exceptions.post_exception import PostNotFoundException
from backend.repositories.post_like_repository import PostLikeRepository


class PostLikeService:
    @classmethod
    def like(
        cls, user_id: str, post_id: str, now: datetime | None = None
    ) -> LikeStateDTO:
        now = now or datetime.now(timezone.utc)
        like_count = PostLikeRepository.like(user_id=user_id, post_id=post_id, now=now)
        if like_count is None:
            raise PostNotFoundException(post_id=post_id)
        return LikeStateDTO(liked=True, likeCount=like_count)

    @classmethod
    def unlike(cls, user_id: str, post_id: str) -> LikeStateDTO:
        like_count = PostLikeRepository.unlike(user_id=user_id, post_id=post_id)
        if like_count is None:
            raise PostNotFoundException(post_id=post_id)
        return LikeStateDTO(liked=False, likeCount=like_count)
