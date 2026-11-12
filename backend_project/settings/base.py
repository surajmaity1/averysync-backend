import os
from pathlib import Path

from dotenv import load_dotenv

from backend.utils.env import env_bool

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

# Automatically load environment variables from .env file
load_dotenv(PROJECT_DIR / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# A weak fallback is only acceptable for local development; production settings
# fail fast if a real SECRET_KEY is not supplied.
INSECURE_DEV_SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
SECRET_KEY = os.getenv("SECRET_KEY", INSECURE_DEV_SECRET_KEY)

DEBUG = env_bool("DEBUG", default=False)

ERROR_DETAILS = env_bool("ERROR_DETAILS", default=False)

ALLOWED_HOSTS = (
    [
        h.strip().strip("'\"[]")
        for h in os.getenv("ALLOWED_HOSTS", "").split(",")
        if h.strip().strip("'\"[]")
    ]
    if os.getenv("ALLOWED_HOSTS")
    else ["localhost", "127.0.0.1", "10.0.2.2"]
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

INSTALLED_APPS = [
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "backend",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "backend.middlewares.jwt_auth.JWTAuthenticationMiddleware",
]

CORS_ALLOWED_ORIGINS = (
    os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if os.getenv("CORS_ALLOWED_ORIGINS")
    else []
)

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

SERVICES = {
    "FRONTEND": {
        "URL": os.getenv("FRONTEND_BASE_URL", "http://localhost:3000"),
        "REDIRECT_PATH": os.getenv("FRONTEND_REDIRECT_PATH", "feed"),
    },
    "BACKEND": {
        "URL": os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Backend API",
    "DESCRIPTION": "Backend project",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/v1/",
    "SWAGGER_UI_SETTINGS": {
        "url": os.getenv("SWAGGER_UI_PATH", "/api/schema"),
    },
    "SERVERS": [
        {
            "url": f"{SERVICES.get('BACKEND').get('URL')}",
            "description": "Dev server",
        },
    ],
    "TAGS": [
        {"name": "health", "description": "Health"},
        {"name": "auth", "description": "Authentication"},
    ],
    "CONTACT": {
        "name": "API Support",
        "email": "surajmaity981@gmail.com",
    },
    "EXTERNAL_DOCS": {
        "description": "Check GitHub Repository",
        "url": "https://github.com/surajmaity1/backend-api-django",
    },
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ROOT_URLCONF = "backend_project.urls"

WSGI_APPLICATION = "backend_project.wsgi.application"

PUBLIC_PATHS = [
    "/favicon.ico",
    "/v1/health",
    "/api/docs",
    "/v1/auth/google/login",
    "/v1/auth/google/callback",
    "/v1/auth/logout",
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Postgres Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "backend_db")
ENGINE = "django.db.backends.postgresql"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
        "OPTIONS": {"options": f"-c search_path={POSTGRES_DB},public"},
    }
}

JWT_CONFIG = {
    "ACCESS_TOKEN_LIFETIME": int(os.getenv("ACCESS_TOKEN_LIFETIME", "3600")),
    "REFRESH_TOKEN_LIFETIME": int(os.getenv("REFRESH_TOKEN_LIFETIME", "604800")),
    "PRIVATE_KEY": os.getenv("PRIVATE_KEY"),
    "PUBLIC_KEY": os.getenv("PUBLIC_KEY"),
    "ALGORITHM": "RS256",
    "ISSUER": os.getenv("JWT_ISSUER", "backend-app-auth"),
}

GOOGLE_OAUTH = {
    "CLIENT_ID": os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    "REDIRECT_URI": os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
    "ALLOWED_REDIRECT_URIS": (
        os.getenv("GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS", "").split(",")
        if os.getenv("GOOGLE_OAUTH_ALLOWED_REDIRECT_URIS")
        else []
    ),
}

COOKIE_SETTINGS = {
    "ACCESS_TOKEN_COOKIE_NAME": os.getenv("ACCESS_TOKEN_COOKIE_NAME", "backend-access"),
    "REFRESH_TOKEN_COOKIE_NAME": os.getenv(
        "REFRESH_TOKEN_COOKIE_NAME", "backend-refresh"
    ),
    "COOKIE_PATH": "/",
    "COOKIE_DOMAIN": os.getenv("COOKIE_DOMAIN", "localhost"),
    "COOKIE_SECURE": os.getenv("COOKIE_SECURE", "True").lower() == "true",
    "COOKIE_HTTPONLY": os.getenv("COOKIE_HTTPONLY", "True").lower() == "true",
    "COOKIE_SAMESITE": os.getenv("COOKIE_SAMESITE", "Strict"),
}

ALLOWED_REDIRECT_SCHEMES = (
    [
        s.strip().strip("'\"[]")
        for s in os.getenv("ALLOWED_REDIRECT_SCHEMES").split(",")
        if s.strip().strip("'\"[]")
    ]
    if os.getenv("ALLOWED_REDIRECT_SCHEMES")
    else ["averysync", "exp"]
)

ALLOWED_REDIRECT_HOSTS = (
    [
        h.strip().strip("'\"[]")
        for h in os.getenv("ALLOWED_REDIRECT_HOSTS").split(",")
        if h.strip().strip("'\"[]")
    ]
    if os.getenv("ALLOWED_REDIRECT_HOSTS")
    else []
)

ALLOWED_NATIVE_REDIRECT_URIS = (
    [
        u.strip().strip("'\"[]")
        for u in os.getenv("ALLOWED_NATIVE_REDIRECT_URIS").split(",")
        if u.strip().strip("'\"[]")
    ]
    if os.getenv("ALLOWED_NATIVE_REDIRECT_URIS")
    else []
)

STREAM_API = os.getenv("STREAM_API", "http://localhost:8999")
STREAM_API_SECRET_KEY = os.getenv("STREAM_API_SECRET_KEY", "")
WEBRTC_ISSUER = os.getenv("WEBRTC_ISSUER", "")
