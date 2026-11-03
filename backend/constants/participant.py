from enum import Enum


class ParticipantRole(Enum):
    HOST = 1
    COHOST = 2
    SPEAKER = 3
    LISTENER = 4


class ParticipantAction(Enum):
    JOIN = 1
    LEAVE = 2
    MUTE = 3
    UNMUTE = 4
    REMOVE = 5
