import base64
import binascii
import uuid
from datetime import datetime


class InvalidCursorError(ValueError):
    pass


def encode_cursor(created_at: datetime, row_id) -> str:
    """Opaque keyset cursor over ``(created_at, id)`` — base64 of ``<iso>|<uuid>``."""
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        iso, row_id = raw.rsplit("|", 1)
        return datetime.fromisoformat(iso), uuid.UUID(row_id)
    except (ValueError, binascii.Error, UnicodeDecodeError) as exception:
        raise InvalidCursorError(str(exception)) from exception
