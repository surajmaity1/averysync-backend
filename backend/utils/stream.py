import jwt
from django.conf import settings

from backend.exceptions.auth_exceptions import TokenInvalidError


class Stream:
    @classmethod
    def stream_voice_peer_to_peer(cls, payload: dict) -> str:
        try:
            print("came inside")
            token = jwt.encode(
                payload=payload, key=settings.STREAM_API_SECRET_KEY, algorithm="HS256"
            )
            print(token)
            return token
        except Exception as exception:
            raise TokenInvalidError(f"stream token generation failed: {str(exception)}")
