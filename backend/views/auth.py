from django.conf import settings
from django.http import HttpResponseRedirect
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.constants.messages import ApplicationMessages
from backend.exceptions.auth_exceptions import AuthException
from backend.services.google_oauth_service import GoogleOAuthService
from backend.services.oauth_state_service import OAuthStateService
from backend.services.user_service import UserService
from backend.utils.jwt_utils import generate_token_pair


class OAuthRedirectResponse(HttpResponseRedirect):
    """
    Subclass of HttpResponseRedirect that allows registered native app custom schemes
    (such as averysync:// or exp://) in addition to http/https.
    """

    def __init__(self, redirect_to: str, *args, **kwargs):
        allowed = getattr(settings, "ALLOWED_REDIRECT_SCHEMES", ["averysync", "exp"])
        self.allowed_schemes = ["http", "https"] + [s.lower() for s in allowed]
        super().__init__(redirect_to, *args, **kwargs)


class GoogleLogInView(APIView):
    @extend_schema(
        operation_id="google_log_in",
        summary="Google OAuth log in",
        description="Redirects to Google OAuth authorization URL or returns JSON response with auth URL",
        tags=["auth"],
        responses={
            200: OpenApiResponse(description="Generated Google OAuth URL"),
            302: OpenApiResponse(description="Redirect to Google OAuth URL"),
        },
    )
    def get(self, request: Request):
        redirect_url = request.query_params.get("redirectURL")
        source_utm = request.query_params.get("sourceUtm")
        is_mobile_param = request.query_params.get("is_mobile")

        is_mobile = (
            source_utm in ("mobile-app", "averysync-mobile")
            or is_mobile_param == "true"
        )
        if redirect_url and (
            redirect_url.startswith("averysync://") or redirect_url.startswith("exp://")
        ):
            is_mobile = True

        if redirect_url and not OAuthStateService.is_safe_redirect_url(redirect_url):
            redirect_url = None

        state = OAuthStateService.generate_state(
            redirect_url=redirect_url, is_mobile=is_mobile
        )
        request.session["oauth_state"] = state

        auth_url, state = GoogleOAuthService.get_authorization_url(
            redirect_url=None, state=state
        )

        if (
            request.headers.get("Accept") == "application/json"
            or request.query_params.get("format") == "json"
        ):
            return Response(
                {
                    "statusCode": status.HTTP_200_OK,
                    "message": "Google OAuth URL generated",
                    "data": {"authUrl": auth_url, "state": state},
                }
            )
        return OAuthRedirectResponse(auth_url)


class GoogleCallbackView(APIView):
    def get(self, request: Request):
        frontend = settings.SERVICES.get("FRONTEND", {})
        frontend_base_url = (
            f"{frontend.get('URL', '')}/{frontend.get('REDIRECT_PATH', '')}"
        )
        is_mobile = False
        client_redirect_url = None

        try:
            code = request.query_params.get("code")
            state = request.query_params.get("state")
            error = request.query_params.get("error")

            is_state_valid = False
            if state:
                try:
                    state_payload = OAuthStateService.verify_and_decode_state(state)
                    is_mobile = bool(state_payload.get("is_mobile", False))
                    client_redirect_url = state_payload.get("redirect_url")

                    if not is_mobile:
                        stored_state = request.session.get("oauth_state")
                        if stored_state and stored_state == state:
                            is_state_valid = True
                    else:
                        is_state_valid = True
                except AuthException:
                    pass

            def _error_redirect(err_code: str) -> OAuthRedirectResponse:
                if is_mobile:
                    target = client_redirect_url or "averysync://google-auth"
                    return OAuthRedirectResponse(
                        OAuthStateService.build_redirect_url(
                            target, {"error": err_code}
                        )
                    )
                return OAuthRedirectResponse(f"{frontend_base_url}?error={err_code}")

            if error:
                return _error_redirect(error)
            if not code:
                return _error_redirect("missing_code")
            if not state:
                return _error_redirect("missing_state")
            if not is_state_valid:
                return _error_redirect("invalid_state")

            google_user_details = GoogleOAuthService.handle_calback(code)
            user = UserService.create_or_update_user(google_user_details)

            tokens = generate_token_pair(
                {
                    "id": str(user.id),
                    "name": user.name,
                }
            )

            request.session.pop("oauth_state", None)

            if is_mobile:
                target = client_redirect_url or "averysync://google-auth"
                if not OAuthStateService.is_safe_redirect_url(target):
                    target = "averysync://google-auth"
                mobile_url = OAuthStateService.build_redirect_url(
                    target,
                    {
                        "access": tokens["access_token"],
                        "refresh": tokens["refresh_token"],
                    },
                )
                return OAuthRedirectResponse(mobile_url)

            target = (
                client_redirect_url
                if (
                    client_redirect_url
                    and OAuthStateService.is_safe_redirect_url(client_redirect_url)
                )
                else frontend_base_url
            )
            response = OAuthRedirectResponse(target)
            self._set_auth_cookies(response, tokens)
            return response

        except Exception:
            if is_mobile:
                target = client_redirect_url or "averysync://google-auth"
                return OAuthRedirectResponse(
                    OAuthStateService.build_redirect_url(
                        target, {"error": "auth_failed"}
                    )
                )
            return OAuthRedirectResponse(f"{frontend_base_url}?error=auth_failed")

    def _get_cookie_config(self):
        return {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
            "httponly": settings.COOKIE_SETTINGS.get("COOKIE_HTTPONLY"),
            "secure": settings.COOKIE_SETTINGS.get("COOKIE_SECURE"),
            "samesite": settings.COOKIE_SETTINGS.get("COOKIE_SAMESITE"),
        }

    def _set_auth_cookies(self, response, tokens):
        config = self._get_cookie_config()

        response.set_cookie(
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME"),
            tokens["access_token"],
            max_age=settings.JWT_CONFIG.get("ACCESS_TOKEN_LIFETIME"),
            **config,
        )

        response.set_cookie(
            settings.COOKIE_SETTINGS.get("REFRESH_TOKEN_COOKIE_NAME"),
            tokens["refresh_token"],
            max_age=settings.JWT_CONFIG.get("REFRESH_TOKEN_LIFETIME"),
            **config,
        )


class LogOutView(APIView):
    def post(self, request: Request):
        request.session.flush()

        response = Response(
            {
                "statusCode": status.HTTP_200_OK,
                "message": ApplicationMessages.GOOGLE_LOGOUT_SUCCESS,
                "data": {"success": True},
            }
        )

        delete_cookies_config = {
            "path": "/",
            "domain": settings.COOKIE_SETTINGS.get("COOKIE_DOMAIN"),
        }
        response.delete_cookie(
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME"),
            **delete_cookies_config,
        )
        response.delete_cookie(
            settings.COOKIE_SETTINGS.get("REFRESH_TOKEN_COOKIE_NAME"),
            **delete_cookies_config,
        )

        delete_session_config = {
            "path": getattr(settings, "SESSION_COOKIE_PATH", "/"),
            "domain": getattr(settings, "SESSION_COOKIE_DOMAIN", "/"),
        }

        response.delete_cookie("sessionid", **delete_session_config)

        return response
