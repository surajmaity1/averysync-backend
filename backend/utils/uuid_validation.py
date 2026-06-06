import uuid


def validate_uuid(uuid_string: str, version=4) -> bool:
    try:
        uuid_obj = uuid.UUID(uuid_string, version=version)
        return str(uuid_obj) == uuid_string.lower() or str(uuid_obj) == uuid_string
    except ValueError:
        return False
