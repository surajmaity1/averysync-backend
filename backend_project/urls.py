from django.urls import path
from django.urls import path, include


urlpatterns = [
    path("v1/", include("backend.urls"), name="api"),
]
