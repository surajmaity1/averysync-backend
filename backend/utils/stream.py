import jwt
from django.conf import settings

from backend.exceptions.auth_exceptions import TokenInvalidError


class Stream:
    @classmethod
    def stream_voice_peer_to_peer(cls, payload: dict) -> str:
        secret = settings.STREAM_API_SECRET_KEY
        if not secret:
            raise TokenInvalidError(
                "stream token generation failed: secret not configured"
            )
        try:
            return jwt.encode(payload=payload, key=secret, algorithm="HS256")
        except Exception as exception:
            raise TokenInvalidError(f"stream token generation failed: {str(exception)}")
