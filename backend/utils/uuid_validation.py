import uuid


def validate_uuid(uuid_string, version=4) -> bool:
    # Django's `<uuid:...>` path converter passes the view an already-parsed
    # uuid.UUID instance (follow/block/followers/following routes), while
    # `<str:...>` routes pass a raw string. A UUID instance is valid by
    # construction; only strings need parsing/validation.
    if isinstance(uuid_string, uuid.UUID):
        return True
    try:
        uuid_obj = uuid.UUID(uuid_string, version=version)
        return str(uuid_obj) == uuid_string.lower() or str(uuid_obj) == uuid_string
    except (ValueError, AttributeError, TypeError):
        return False
