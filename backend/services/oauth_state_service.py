import secrets
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.utils.http import url_has_allowed_host_and_scheme

from backend.constants.messages import ApiErrors
from backend.exceptions.auth_exceptions import AuthException

STATE_SALT = "averysync.oauth.state"
NONCE_CACHE_KEY = "oauth_state_nonce:{}"


class OAuthStateService:
    DEFAULT_STATE_MAX_AGE_SECONDS: int = 600

    @classmethod
    def generate_state(
        cls,
        redirect_url: str | None = None,
        is_mobile: bool = False,
    ) -> str:
        nonce = secrets.token_urlsafe(16)
        cache.set(
            NONCE_CACHE_KEY.format(nonce),
            1,
            timeout=cls.DEFAULT_STATE_MAX_AGE_SECONDS,
        )
        payload: dict[str, Any] = {
            "redirect_url": redirect_url,
            "is_mobile": is_mobile,
            "nonce": nonce,
        }
        return signing.dumps(payload, salt=STATE_SALT)

    @classmethod
    def verify_and_decode_state(
        cls,
        state: str,
        max_age: int = DEFAULT_STATE_MAX_AGE_SECONDS,
    ) -> dict[str, Any]:
        if not state or not isinstance(state, str):
            raise AuthException(ApiErrors.GOOGLE_AUTH_FAILED)
        try:
            payload = signing.loads(state, salt=STATE_SALT, max_age=max_age)
        except signing.BadSignature as err:
            raise AuthException(ApiErrors.GOOGLE_AUTH_FAILED) from err

        if not isinstance(payload, dict):
            raise AuthException(ApiErrors.GOOGLE_AUTH_FAILED)

        nonce = payload.get("nonce")
        # Single-use: cache.delete returns True only if the key existed
        if not nonce or not cache.delete(NONCE_CACHE_KEY.format(nonce)):
            raise AuthException(ApiErrors.GOOGLE_AUTH_FAILED)

        return payload

    @classmethod
    def is_safe_redirect_url(cls, url: str | None) -> bool:
        if not url or not isinstance(url, str):
            return False

        try:
            parsed = urlparse(url)
        except ValueError:
            return False

        scheme = parsed.scheme.lower()
        if not scheme:
            return False

        if scheme in ("http", "https"):
            allowed_hosts: set[str] = set(
                getattr(settings, "ALLOWED_REDIRECT_HOSTS", [])
            )

            frontend_url = (
                settings.SERVICES.get("FRONTEND", {}).get("URL")
                if hasattr(settings, "SERVICES")
                else None
            )
            if frontend_url:
                frontend_netloc = urlparse(frontend_url).netloc
                if frontend_netloc:
                    allowed_hosts.add(frontend_netloc)

            return url_has_allowed_host_and_scheme(
                url,
                allowed_hosts=allowed_hosts,
                require_https=not settings.DEBUG,
            )

        if scheme == "exp" and settings.DEBUG:
            return True

        native_uris: set[str] = set(
            getattr(settings, "ALLOWED_NATIVE_REDIRECT_URIS", [])
        )
        canonical = f"{scheme}://{parsed.netloc}{parsed.path}"
        return canonical in native_uris

    @classmethod
    def build_redirect_url(cls, base_url: str, params: dict[str, str]) -> str:
        parsed = urlparse(base_url)
        pairs = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k not in params  # server-supplied params win
        ]
        pairs.extend(params.items())
        return urlunparse(parsed._replace(query=urlencode(pairs)))
