from .base import *

DEBUG = True
ERROR_DETAILS = True
ALLOWED_HOSTS = ["*"]

ALLOWED_REDIRECT_HOSTS = ["localhost", "localhost:3000", "127.0.0.1", "127.0.0.1:3000"]
ALLOWED_NATIVE_REDIRECT_URIS = ["averysync://auth/callback", "averysync://google-auth"]
