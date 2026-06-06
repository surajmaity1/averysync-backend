from enum import Enum


class PostType(Enum):
    POST = "POST"
    SPACE = "SPACE"


class SpaceStatus(Enum):
    SCHEDULED = 1
    LIVE = 2
    ENDED = 3
    CLOSED = 4
