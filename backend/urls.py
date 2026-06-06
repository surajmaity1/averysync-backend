from django.urls import path
from backend.views.auth import GoogleLogInView, GoogleCallbackView, LogOutView
from backend.views.health import HealthView
from backend.views.user import UsersView, UserDetailView
from backend.views.post import PostView, PostDetailView, ReminderView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("auth/google/login", GoogleLogInView.as_view(), name="google_log_in"),
    path("auth/google/callback", GoogleCallbackView.as_view(), name="google_callback"),
    path("auth/logout", LogOutView.as_view(), name="logout"),
    path("users", UsersView.as_view(), name="users"),
    path("users/<str:user_id>", UserDetailView.as_view(), name="user_detail"),
    path("posts", PostView.as_view(), name="posts"),
    path("posts/<str:post_id>", PostDetailView.as_view(), name="post_detail"),
    path(
        "posts/<uuid:space_id>/reminders",
        ReminderView.as_view(),
        name="posts_reminders",
    ),
]
