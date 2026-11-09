from enum import Enum


class FollowStatus(Enum):
    PENDING = 1
    ACCEPTED = 2


class RelationshipStatus(Enum):
    NONE = "NONE"
    PENDING = "PENDING"
    FOLLOWING = "FOLLOWING"
    SELF = "SELF"


class FollowRequestAction(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
