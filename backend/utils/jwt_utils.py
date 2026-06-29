from django.conf import settings
from datetime import datetime, timezone, timedelta
import jwt
from backend.exceptions.auth_exceptions import (
    TokenInvalidError,
    AuthErrorMessages,
    TokenExpiredError,
)


def generate_token(user_details: dict, token_type: str) -> str:
    try:
        issued_at = datetime.now(timezone.utc)
        expired = issued_at + timedelta(
            seconds=settings.JWT_CONFIG.get(f"{token_type.upper()}_TOKEN_LIFETIME")
        )

        payload = {
            "iss": settings.JWT_CONFIG.get("ISSUER"),
            "iat": int(issued_at.timestamp()),
            "exp": int(expired.timestamp()),
            "token_type": f"{token_type.lower()}",
            "sub": user_details["id"],
            "user_id": user_details["id"],
        }

        token = jwt.encode(
            payload=payload,
            key=settings.JWT_CONFIG.get("PRIVATE_KEY"),
            algorithm=settings.JWT_CONFIG.get("ALGORITHM"),
        )

        return token
    except Exception as exception:
        raise TokenInvalidError(
            f"{token_type} token generation failed: {str(exception)}"
        )


def validate_token(token: str, token_type: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.JWT_CONFIG.get("PUBLIC_KEY"),
            algorithms=[settings.JWT_CONFIG.get("ALGORITHM")],
            issuer=settings.JWT_CONFIG.get("ISSUER"),
            options={"require": ["exp", "iss", "user_id", "token_type"]},
        )

        if payload.get("token_type") != token_type.lower():
            raise TokenInvalidError(AuthErrorMessages.TOKEN_INVALID)

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError as error:
        raise TokenInvalidError(f"Invalid {token_type} token: {str(error)}")
    except Exception as exception:
        raise TokenInvalidError(
            f"{token_type} token validation faled: {str(exception)}"
        )


def generate_token_pair(user_details: dict) -> dict:
    access_token = generate_token(user_details, "Access")
    refresh_token = generate_token(user_details, "Refresh")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_CONFIG.get("ACCESS_TOKEN_LIFETIME"),
    }
