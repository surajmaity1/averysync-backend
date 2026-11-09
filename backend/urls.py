from django.urls import path
from backend.views.auth import GoogleLogInView, GoogleCallbackView, LogOutView
from backend.views.health import HealthView
from backend.views.user import UsersView, UserDetailView
from backend.views.post import PostView, PostDetailView, ReminderView
from backend.views.space_participant import (
    ParticipantsView,
    ParticipantDetailView,
    ParticipantMuteView,
)
from backend.views.follow import (
    FollowView,
    FollowersView,
    FollowingView,
    FollowRequestsView,
    FollowRequestActionView,
    FollowerRemoveView,
)
from backend.views.block import BlockView, BlocksView
from backend.views.conversation import (
    ConversationsView,
    ConversationDetailView,
    ConversationAcceptView,
    ConversationDeclineView,
    ConversationReadView,
    ConversationUnreadCountView,
)
from backend.views.message import MessagesView
from backend.views.post_like import PostLikeView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("auth/google/login", GoogleLogInView.as_view(), name="google_log_in"),
    path("auth/google/callback", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/logout", LogOutView.as_view(), name="logout"),
    path("users", UsersView.as_view(), name="users"),
    path(
        "users/<uuid:user_id>/follow",
        FollowView.as_view(),
        name="user_follow",
    ),
    path(
        "users/<uuid:user_id>/followers",
        FollowersView.as_view(),
        name="user_followers",
    ),
    path(
        "users/<uuid:user_id>/following",
        FollowingView.as_view(),
        name="user_following",
    ),
    path(
        "users/<uuid:user_id>/block",
        BlockView.as_view(),
        name="user_block",
    ),
    path(
        "requests/follow",
        FollowRequestsView.as_view(),
        name="requests_follow",
    ),
    path(
        "requests/follow/<uuid:follower_id>",
        FollowRequestActionView.as_view(),
        name="follow_request_action",
    ),
    path(
        "followers/<uuid:follower_id>",
        FollowerRemoveView.as_view(),
        name="follower_remove",
    ),
    path("blocks", BlocksView.as_view(), name="blocks"),
    path("conversations", ConversationsView.as_view(), name="conversations"),
    path(
        "conversations/unread-count",
        ConversationUnreadCountView.as_view(),
        name="conversation_unread_count",
    ),
    path(
        "conversations/<uuid:conversation_id>/read",
        ConversationReadView.as_view(),
        name="conversation_read",
    ),
    path(
        "conversations/<uuid:conversation_id>",
        ConversationDetailView.as_view(),
        name="conversation_detail",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages",
        MessagesView.as_view(),
        name="conversation_messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/accept",
        ConversationAcceptView.as_view(),
        name="conversation_accept",
    ),
    path(
        "conversations/<uuid:conversation_id>/decline",
        ConversationDeclineView.as_view(),
        name="conversation_decline",
    ),
    path("users/<str:user_id>", UserDetailView.as_view(), name="user_detail"),
    path("posts", PostView.as_view(), name="posts"),
    path(
        "posts/<uuid:post_id>/like",
        PostLikeView.as_view(),
        name="post_like",
    ),
    path("posts/<str:post_id>", PostDetailView.as_view(), name="post_detail"),
    path(
        "posts/<uuid:space_id>/reminders",
        ReminderView.as_view(),
        name="posts_reminders",
    ),
    path(
        "posts/<str:space_id>/participants",
        ParticipantsView.as_view(),
        name="posts_participants",
    ),
    path(
        "posts/<str:space_id>/participants/<str:user_id>",
        ParticipantDetailView.as_view(),
        name="posts_participant_detail",
    ),
    path(
        "posts/<str:space_id>/participants/<str:user_id>/mute",
        ParticipantMuteView.as_view(),
        name="posts_participant_mute",
    ),
]
