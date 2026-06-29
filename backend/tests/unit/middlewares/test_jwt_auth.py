import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory
from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from backend.exceptions.auth_exceptions import TokenExpiredError, TokenInvalidError
from backend.middlewares.jwt_auth import JWTAuthenticationMiddleware

COOKIE_SETTINGS = {
    "ACCESS_TOKEN_COOKIE_NAME": "backend-access",
    "REFRESH_TOKEN_COOKIE_NAME": "backend-refresh",
    "COOKIE_DOMAIN": "localhost",
    "COOKIE_SECURE": True,
    "COOKIE_SAMESITE": "Strict",
}

JWT_CONFIG = {"ACCESS_TOKEN_LIFETIME": 3600}

PUBLIC_PATHS = ["/v1/health", "/v1/auth/logout"]

CORS_ALLOWED_ORIGINS = ["https://app.example.com"]


def make_middleware(get_response=None):
    return JWTAuthenticationMiddleware(get_response or (lambda request: MagicMock()))


@override_settings(PUBLIC_PATHS=PUBLIC_PATHS)
class CheckPublicPathTests(TestCase):
    def setUp(self):
        self.mw = make_middleware()

    def test_exact_public_path_is_public(self):
        self.assertTrue(self.mw._check_public_path("/v1/health"))

    def test_subpath_of_public_path_is_public(self):
        self.assertTrue(self.mw._check_public_path("/v1/health/live"))

    def test_prefix_lookalike_is_not_public(self):
        self.assertFalse(self.mw._check_public_path("/v1/healthcheck-secret"))

    def test_protected_path_is_not_public(self):
        self.assertFalse(self.mw._check_public_path("/v1/posts"))


@override_settings(
    PUBLIC_PATHS=PUBLIC_PATHS,
    COOKIE_SETTINGS=COOKIE_SETTINGS,
    CORS_ALLOWED_ORIGINS=CORS_ALLOWED_ORIGINS,
    ERROR_DETAILS=False,
)
class CsrfOriginTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_unsafe_method_with_foreign_origin_is_rejected(self):
        downstream = MagicMock()
        mw = make_middleware(lambda request: downstream)
        request = self.factory.post("/v1/posts", HTTP_ORIGIN="https://evil.example.com")

        response = mw(request)

        self.assertEqual(response.status_code, 403)
        downstream.assert_not_called

    def test_unsafe_method_with_allowed_origin_proceeds_to_auth(self):
        mw = make_middleware(lambda request: MagicMock(status_code=200))
        request = self.factory.post("/v1/posts", HTTP_ORIGIN="https://app.example.com")

        with patch.object(mw, "_authentication", return_value=False) as mock_auth:
            response = mw(request)

        mock_auth.assert_called_once()
        self.assertEqual(response.status_code, 401)

    def test_safe_method_skips_origin_check(self):
        mw = make_middleware(lambda request: MagicMock(status_code=200))
        request = self.factory.get("/v1/posts", HTTP_ORIGIN="https://evil.example.com")

        with patch.object(mw, "_authentication", return_value=False):
            response = mw(request)

        self.assertEqual(response.status_code, 401)

    def test_public_path_skips_origin_check(self):
        sentinel = MagicMock(status_code=200)
        mw = make_middleware(lambda request: sentinel)
        request = self.factory.post(
            "/v1/auth/logout", HTTP_ORIGIN="https://evil.example.com"
        )

        response = mw(request)

        self.assertIs(response, sentinel)


@override_settings(
    PUBLIC_PATHS=PUBLIC_PATHS,
    COOKIE_SETTINGS=COOKIE_SETTINGS,
    JWT_CONFIG=JWT_CONFIG,
)
class RefreshFlowTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("backend.middlewares.jwt_auth.UserRepository.get_by_id")
    @patch("backend.middlewares.jwt_auth.generate_token", return_value="new-access")
    @patch("backend.middlewares.jwt_auth.validate_token")
    def test_expired_access_with_valid_refresh_reauthenticates(
        self, mock_validate, mock_generate, mock_get_by_id
    ):
        mock_get_by_id.return_value = MagicMock(email="u@example.com")

        def validate(token, token_type):
            if token_type == "Access":
                raise TokenExpiredError()
            return {"user_id": "user-1"}

        mock_validate.side_effect = validate

        captured = {}

        def get_response(request):
            captured["user_id"] = getattr(request, "user_id", None)
            from django.http import HttpResponse

            return HttpResponse(status=200)

        mw = make_middleware(get_response)
        request = self.factory.get("/v1/posts")
        request.COOKIES["backend-access"] = "expired"
        request.COOKIES["backend-refresh"] = "valid-refresh"

        response = mw(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["user_id"], "user-1")
        mock_generate.assert_called_once()
        self.assertIn("backend-access", response.cookies)
        self.assertEqual(response.cookies["backend-access"].value, "new-access")

    @patch("backend.middlewares.jwt_auth.validate_token")
    def test_invalid_access_no_refresh_returns_401(self, mock_validate):
        mock_validate.side_effect = TokenInvalidError()

        mw = make_middleware(lambda request: MagicMock(status_code=200))
        request = self.factory.get("/v1/posts")
        request.COOKIES["backend-access"] = "garbage"

        response = mw(request)

        self.assertEqual(response.status_code, 401)
        body = json.loads(response.content)
        self.assertEqual(body["statusCode"], 401)
