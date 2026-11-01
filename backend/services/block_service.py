from django.db import transaction

from backend.dto.block_dto import BlockDTO, BlockUserDTO
from backend.dto.responses.get_blocks_response import GetBlocksResponse
from backend.exceptions.follow_exception import CannotBlockSelfException
from backend.models.block import UserBlockModel
from backend.repositories.block_repository import BlockRepository
from backend.repositories.follow_repository import FollowRepository
from backend.repositories.user_repositories import UserRepository


class BlockService:
    @classmethod
    def _prepare_block_dto(cls, block: UserBlockModel) -> BlockDTO:
        return BlockDTO(
            id=block.id,
            blockerId=block.blocker_id,
            blockedId=block.blocked_id,
            createdAt=block.created_at,
        )

    @classmethod
    def block(cls, blocker_id: str, target_user_id: str) -> tuple[BlockDTO, bool]:
        if blocker_id == target_user_id:
            raise CannotBlockSelfException()

        UserRepository.get_by_id(target_user_id)

        with transaction.atomic():
            FollowRepository.soft_delete(
                follower_id=blocker_id, followee_id=target_user_id
            )
            FollowRepository.soft_delete(
                follower_id=target_user_id, followee_id=blocker_id
            )
            block, created = BlockRepository.create_or_reactivate(
                blocker_id=blocker_id, blocked_id=target_user_id
            )
        return cls._prepare_block_dto(block), created

    @classmethod
    def unblock(cls, blocker_id: str, target_user_id: str) -> None:
        BlockRepository.soft_delete(blocker_id=blocker_id, blocked_id=target_user_id)
        return None

    @classmethod
    def get_blocks(cls, user_id: str, limit: int, offset: int) -> GetBlocksResponse:
        blocks, total = BlockRepository.list_blocks(
            user_id=user_id, limit=limit, offset=offset
        )
        data = [
            BlockUserDTO(
                id=block.blocked.id,
                name=block.blocked.name,
                image=block.blocked.image,
                blockedAt=block.created_at,
            )
            for block in blocks
        ]
        return GetBlocksResponse(data=data, total=total, limit=limit, offset=offset)
