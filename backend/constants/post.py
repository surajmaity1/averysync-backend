from enum import Enum


class PostType(Enum):
    POST = 'POST'
    SPACE = 'SPACE'


class SpaceStatus(Enum):
    OPEN = 1
    CLOSED = 2
