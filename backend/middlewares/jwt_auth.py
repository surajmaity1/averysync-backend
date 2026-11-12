from django.conf import settings
from backend.utils.jwt_utils import validate_token, generate_token
from backend.repositories.user_repositories import UserRepository
from backend.exceptions.auth_exceptions import (
    TokenInvalidError,
    AuthErrorMessages,
    TokenExpiredError,
    RefreshTokenExpiredError,
    ApiErrors,
    TokenMissingError,
)
from backend.dto.responses.error_response import ApiErrorResponse, ApiErrorDetail
from rest_framework import status
from django.http import JsonResponse


class JWTAuthenticationMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    def __call__(self, request):
        try:
            if self._check_public_path(request.path):
                return self.get_response(request)

            if not self._passes_csrf(request):
                return self._forbidden_csrf_response()

            is_authenticated = self._authentication(request)

            if is_authenticated:
                response = self.get_response(request)
                return self._process_response(request, response)
            else:
                error_response = ApiErrorResponse(
                    statusCode=status.HTTP_401_UNAUTHORIZED,
                    message=AuthErrorMessages.UNAUTHENTICATED_REQUIRED,
                    errors=[
                        ApiErrorDetail(
                            title=ApiErrors.AUTHENTICATION_FAILED,
                            description=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                        )
                    ]
                    if settings.ERROR_DETAILS
                    else AuthErrorMessages.AUTHENTICATION_REQUIRED,
                )

                return JsonResponse(
                    data=error_response.model_dump(mode="json", exclude_none=True),
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        except (TokenMissingError, TokenExpiredError, TokenInvalidError) as exception:
            return self._handle_authentication_error(exception)
        except Exception:
            error_response = ApiErrorResponse(
                statusCode=status.HTTP_401_UNAUTHORIZED,
                message=ApiErrors.AUTHENTICATION_FAILED,
                errors=[
                    ApiErrorDetail(
                        title=ApiErrors.AUTHENTICATION_FAILED,
                        description=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                    )
                ]
                if settings.ERROR_DETAILS
                else AuthErrorMessages.AUTHENTICATION_FAILED,
            )

            return JsonResponse(
                data=error_response.model_dump(mode="json", exclude_none=True),
                status=status.HTTP_401_UNAUTHORIZED,
            )

    def _handle_authentication_error(self, exception):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_401_UNAUTHORIZED,
            message=str(exception),
            errors=[
                ApiErrorDetail(
                    title=ApiErrors.AUTHENTICATION_FAILED,
                    description=str(exception),
                )
            ]
            if settings.ERROR_DETAILS
            else AuthErrorMessages.AUTHENTICATION_FAILED,
        )
        return JsonResponse(
            error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_401_UNAUTHORIZED,
        )

    def _process_response(self, request, response):
        if hasattr(request, "_new_access_token"):
            config = self._get_cookie_config()
            response.set_cookie(
                settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME"),
                request._new_access_token,
                max_age=request._access_token_expires,
                **config,
            )
        return response

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "httponly": True,
            "secure": settings.COOKIE_SETTINGS.get("COOKIE_SECURE"),
            "samesite": settings.COOKIE_SETTINGS.get("COOKIE_SAMESITE"),
        }

    def _check_public_path(self, path: str) -> bool:
        return any(
            path == public_path or path.startswith(public_path.rstrip("/") + "/")
            for public_path in settings.PUBLIC_PATHS
        )

    def _passes_csrf(self, request) -> bool:
        if request.method in self.SAFE_METHODS:
            return True

        origin = request.headers.get("Origin")
        if not origin:
            return True

        return origin in set(getattr(settings, "CORS_ALLOWED_ORIGINS", []))

    def _forbidden_csrf_response(self):
        error_response = ApiErrorResponse(
            statusCode=status.HTTP_403_FORBIDDEN,
            message=ApiErrors.AUTHENTICATION_FAILED.format(
                "cross-origin request blocked"
            ),
            errors=[
                ApiErrorDetail(
                    title=ApiErrors.AUTHENTICATION_FAILED.format(
                        "cross-origin request blocked"
                    ),
                    description=AuthErrorMessages.AUTHENTICATION_REQUIRED,
                )
            ]
            if settings.ERROR_DETAILS
            else AuthErrorMessages.AUTHENTICATION_REQUIRED,
        )
        return JsonResponse(
            data=error_response.model_dump(mode="json", exclude_none=True),
            status=status.HTTP_403_FORBIDDEN,
        )

    def _set_user_data(self, request, payload):
        user_id = payload["user_id"]
        user = UserRepository.get_by_id(user_id)

        if not user:
            raise TokenInvalidError(AuthErrorMessages.TOKEN_INVALID)

        request.user_id = user_id
        request.user_email = user.email

    def _get_access_token(self, request) -> str | None:
        auth_header = request.headers.get("Authorization") or request.META.get(
            "HTTP_AUTHORIZATION"
        )
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1].strip()

        return request.COOKIES.get(
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME")
        )

    def _get_refresh_token(self, request) -> str | None:
        refresh_header = request.headers.get("X-Refresh-Token") or request.META.get(
            "HTTP_X_REFRESH_TOKEN"
        )
        if refresh_header:
            return refresh_header.strip()

        return request.COOKIES.get(
            settings.COOKIE_SETTINGS.get("REFRESH_TOKEN_COOKIE_NAME")
        )

    def _refresh_token(self, request) -> bool:
        try:
            refresh_token = self._get_refresh_token(request)

            if not refresh_token:
                return False

            payload = validate_token(refresh_token, "Refresh")
            user_details = {
                "id": payload["user_id"],
            }
            generate_new_access_token = generate_token(user_details, "Access")
            self._set_user_data(request, payload)
            request._new_access_token = generate_new_access_token
            request._access_token_expires = settings.JWT_CONFIG["ACCESS_TOKEN_LIFETIME"]

            return True
        except (RefreshTokenExpiredError, TokenInvalidError):
            return False
        except Exception:
            return False

    def _authentication(self, request) -> bool:
        try:
            access_token = self._get_access_token(request)

            if access_token:
                try:
                    payload = validate_token(access_token, "Access")
                    self._set_user_data(request, payload)
                    return True
                except (TokenInvalidError, TokenExpiredError):
                    pass

            return self._refresh_token(request)
        except (TokenExpiredError, TokenInvalidError) as e:
            raise e
        except Exception:
            return False
