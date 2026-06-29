from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import (
    INSECURE_DEV_SECRET_KEY,
    JWT_CONFIG,
    SECRET_KEY,
)

DEBUG = False
ERROR_DETAILS = False

_required = {
    "SECRET_KEY": SECRET_KEY if SECRET_KEY != INSECURE_DEV_SECRET_KEY else None,
    "JWT private key": JWT_CONFIG.get("PRIVATE_KEY"),
    "JWT public key": JWT_CONFIG.get("PUBLIC_KEY"),
}
_missing = [name for name, value in _required.items() if not value]
if _missing:
    raise ImproperlyConfigured(
        f"Missing required production configuration: {', '.join(_missing)}"
    )

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
