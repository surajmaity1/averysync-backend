from unittest.mock import MagicMock, patch

import jwt
import requests
from django.test import SimpleTestCase, override_settings

from backend.utils.sfu import Sfu

SFU_PATH = "backend.utils.sfu"


@override_settings(
    STREAM_API="http://sfu.local:8080",
    STREAM_API_SECRET_KEY="a-real-secret",
    WEBRTC_ISSUER="backend-webrtc-issuer",
    WEBRTC_AUDIENCE="stream-go-service",
)
class SfuPushMuteTests(SimpleTestCase):
    def _ok_response(self):
        response = MagicMock()
        response.raise_for_status.return_value = None
        return response

    @patch(f"{SFU_PATH}.requests.post")
    def test_posts_to_room_mute_endpoint_with_payload(self, mock_post):
        mock_post.return_value = self._ok_response()

        Sfu.push_mute(
            space_id="space-1",
            user_id="listener-1",
            is_muted=True,
            muted_until=1_700_000_000,
        )

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://sfu.local:8080/rooms/space-1/mute")
        self.assertEqual(
            kwargs["json"],
            {"userId": "listener-1", "isMuted": True, "mutedUntil": 1_700_000_000},
        )
        self.assertIn("timeout", kwargs)

    @patch(f"{SFU_PATH}.requests.post")
    def test_authorizes_with_room_scoped_host_service_token(self, mock_post):
        mock_post.return_value = self._ok_response()

        Sfu.push_mute(space_id="space-1", user_id="listener-1", is_muted=False)

        _, kwargs = mock_post.call_args
        auth_header = kwargs["headers"]["Authorization"]
        self.assertTrue(auth_header.startswith("Bearer "))
        token = auth_header.removeprefix("Bearer ")
        claims = jwt.decode(
            token,
            "a-real-secret",
            algorithms=["HS256"],
            audience="stream-go-service",
        )
        self.assertEqual(claims["room_id"], "space-1")
        self.assertTrue(claims["is_host"])
        self.assertEqual(claims["iss"], "backend-webrtc-issuer")
        self.assertIn("exp", claims)

    @patch(f"{SFU_PATH}.requests.post")
    def test_unmute_sends_null_muted_until(self, mock_post):
        mock_post.return_value = self._ok_response()

        Sfu.push_mute(space_id="space-1", user_id="listener-1", is_muted=False)

        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["json"],
            {"userId": "listener-1", "isMuted": False, "mutedUntil": None},
        )

    @patch(f"{SFU_PATH}.requests.post")
    def test_raises_on_http_error(self, mock_post):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_post.return_value = response

        with self.assertRaises(requests.HTTPError):
            Sfu.push_mute(space_id="space-1", user_id="listener-1", is_muted=True)

    @patch(f"{SFU_PATH}.requests.post", side_effect=requests.ConnectionError("refused"))
    def test_propagates_connection_error(self, mock_post):
        with self.assertRaises(requests.ConnectionError):
            Sfu.push_mute(space_id="space-1", user_id="listener-1", is_muted=True)
