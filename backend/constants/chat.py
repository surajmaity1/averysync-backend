from enum import Enum


class ConversationType(Enum):
    DIRECT = 1
    GROUP = 2


class MemberRole(Enum):
    OWNER = 1
    ADMIN = 2
    MEMBER = 3


class MemberState(Enum):
    PENDING = 1
    ACCEPTED = 2


class MessageType(Enum):
    TEXT = 1
    IMAGE = 2
    VIDEO = 3
    VOICE = 4
    LINK = 5
    SYSTEM = 6


class ConversationSection(Enum):
    # Inbox placement, keyed off the caller's membership state.
    PRIMARY = "primary"  # ACCEPTED memberships
    REQUESTS = "requests"  # PENDING memberships (message requests)
