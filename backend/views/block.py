from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.services.block_service import BlockService
from backend.utils.uuid_validation import validate_uuid
from backend.views.follow import FollowErrorMixin


class BlockView(FollowErrorMixin, APIView):
    def post(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            dto, created = BlockService.block(
                blocker_id=request.user_id, target_user_id=user_id
            )
            return Response(
                data={"data": dto.model_dump(mode="json")},
                status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)

    def delete(self, request: Request, user_id: str):
        if not validate_uuid(uuid_string=user_id):
            return self._bad_uuid(user_id)
        try:
            BlockService.unblock(blocker_id=request.user_id, target_user_id=user_id)
            return Response(data=None, status=status.HTTP_204_NO_CONTENT)
        except Exception as exception:
            return self._handle_domain_exception(exception)


class BlocksView(FollowErrorMixin, APIView):
    def get(self, request: Request):
        page, error = self._paginate(request)
        if error is not None:
            return error
        try:
            response = BlockService.get_blocks(
                user_id=request.user_id,
                limit=page["limit"],
                offset=page["offset"],
            )
            return Response(
                data=response.model_dump(mode="json"), status=status.HTTP_200_OK
            )
        except Exception as exception:
            return self._handle_domain_exception(exception)
