import time

import jwt
import requests
from django.conf import settings


class Sfu:
    TIMEOUT_SECONDS = 3
    TOKEN_LIFETIME_SECONDS = 60

    @classmethod
    def push_mute(
        cls,
        space_id: str,
        user_id: str,
        is_muted: bool,
        muted_until: int | None = None,
        now: int | None = None,
    ) -> requests.Response:
        token = cls._service_token(space_id=space_id, now=now)
        url = f"{settings.STREAM_API}/rooms/{space_id}/mute"
        response = requests.post(
            url,
            json={
                "userId": str(user_id),
                "isMuted": is_muted,
                "mutedUntil": muted_until,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=cls.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    @classmethod
    def _service_token(cls, space_id: str, now: int | None = None) -> str:
        issued_at = now if now is not None else int(time.time())
        payload = {
            "user_id": "backend-service",
            "username": "backend-service",
            "room_id": str(space_id),
            "is_host": True,
            "iss": getattr(settings, "WEBRTC_ISSUER"),
            "aud": getattr(settings, "WEBRTC_AUDIENCE"),
            "exp": issued_at + cls.TOKEN_LIFETIME_SECONDS,
        }
        return jwt.encode(payload, settings.STREAM_API_SECRET_KEY, algorithm="HS256")
