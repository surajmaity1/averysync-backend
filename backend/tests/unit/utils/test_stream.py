import jwt
from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from backend.exceptions.auth_exceptions import TokenInvalidError
from backend.utils.stream import Stream


class StreamTokenTests(TestCase):
    @override_settings(STREAM_API_SECRET_KEY="a-real-secret")
    def test_returns_signed_token_when_secret_configured(self):
        payload = {"user_id": "u1", "room_id": "r1", "is_speaker": True}

        token = Stream.stream_voice_peer_to_peer(payload=payload)

        decoded = jwt.decode(token, "a-real-secret", algorithms=["HS256"])
        self.assertEqual(decoded["user_id"], "u1")
        self.assertTrue(decoded["is_speaker"])

    @override_settings(STREAM_API_SECRET_KEY="")
    def test_raises_when_secret_missing(self):
        with self.assertRaises(TokenInvalidError):
            Stream.stream_voice_peer_to_peer(payload={"user_id": "u1"})

    @override_settings(STREAM_API_SECRET_KEY=None)
    def test_raises_when_secret_is_none(self):
        with self.assertRaises(TokenInvalidError):
            Stream.stream_voice_peer_to_peer(payload={"user_id": "u1"})

    @override_settings(STREAM_API_SECRET_KEY="a-real-secret")
    def test_does_not_print_token(self):
        import builtins
        from unittest.mock import patch

        with patch.object(builtins, "print") as mock_print:
            Stream.stream_voice_peer_to_peer(payload={"user_id": "u1"})

        mock_print.assert_not_called()
