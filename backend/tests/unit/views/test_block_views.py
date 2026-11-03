import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from rest_framework import status

from backend.dto.block_dto import BlockDTO, BlockUserDTO
from backend.dto.responses.get_blocks_response import GetBlocksResponse
from backend.exceptions.auth_exceptions import UserNotFoundException
from backend.exceptions.follow_exception import CannotBlockSelfException
from backend.views.block import BlocksView, BlockView

NOW = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
SERVICE = "backend.views.block.BlockService"


def _block_dto(blocker_id, blocked_id):
    return BlockDTO(
        id=uuid.uuid4(),
        blockerId=blocker_id,
        blockedId=blocked_id,
        createdAt=NOW,
    )


class BlockViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())
        self.target_id = str(uuid.uuid4())

    def _post(self, user_id):
        request = self.factory.post(
            "/v1/users/x/block", data=json.dumps({}), content_type="application/json"
        )
        request.user_id = self.caller_id
        return BlockView.as_view()(request, user_id=user_id)

    def _delete(self, user_id):
        request = self.factory.delete("/v1/users/x/block")
        request.user_id = self.caller_id
        return BlockView.as_view()(request, user_id=user_id)

    @patch(f"{SERVICE}.block")
    def test_block_new_returns_201(self, mocked):
        mocked.return_value = (_block_dto(self.caller_id, self.target_id), True)
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{SERVICE}.block")
    def test_block_existing_returns_200(self, mocked):
        mocked.return_value = (_block_dto(self.caller_id, self.target_id), False)
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch(f"{SERVICE}.block")
    def test_block_self_returns_400(self, mocked):
        mocked.side_effect = CannotBlockSelfException()
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.block")
    def test_block_accepts_uuid_object_from_path_converter(self, mocked):
        # The `<uuid:user_id>` route converter hands the view a uuid.UUID
        # instance, not a string. Regression for the 500 crash where
        # validate_uuid() called uuid.UUID() on an already-parsed UUID.
        target = uuid.UUID(self.target_id)
        mocked.return_value = (_block_dto(self.caller_id, self.target_id), True)
        response = self._post(target)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch(f"{SERVICE}.block")
    def test_block_missing_target_returns_404(self, mocked):
        mocked.side_effect = UserNotFoundException()
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_bad_uuid_returns_400(self):
        response = self._post("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.unblock")
    def test_unblock_returns_204(self, mocked):
        mocked.return_value = None
        response = self._delete(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unblock_bad_uuid_returns_400(self):
        response = self._delete("not-a-uuid")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.unblock")
    def test_unblock_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._delete(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch(f"{SERVICE}.block")
    def test_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        response = self._post(self.target_id)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class BlocksViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.caller_id = str(uuid.uuid4())

    @patch(f"{SERVICE}.get_blocks")
    def test_returns_200(self, mocked):
        mocked.return_value = GetBlocksResponse(
            data=[BlockUserDTO(id=uuid.uuid4(), name="Zed", blockedAt=NOW)],
            total=1,
            limit=20,
            offset=0,
        )
        request = self.factory.get("/v1/blocks")
        request.user_id = self.caller_id
        response = BlocksView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total"], 1)

    def test_invalid_pagination_returns_400(self):
        request = self.factory.get("/v1/blocks?limit=0")
        request.user_id = self.caller_id
        response = BlocksView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch(f"{SERVICE}.get_blocks")
    def test_unexpected_error_returns_500(self, mocked):
        mocked.side_effect = RuntimeError("boom")
        request = self.factory.get("/v1/blocks")
        request.user_id = self.caller_id
        response = BlocksView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
