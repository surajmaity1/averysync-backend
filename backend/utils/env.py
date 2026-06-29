import os

_TRUTHY = {"1", "true", "yes", "on"}


def env_bool(name: str, default: bool = False, _getenv=os.getenv) -> bool:
    raw = _getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY
