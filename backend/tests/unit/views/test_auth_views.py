from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from backend.constants.messages import ApplicationMessages
from backend.services.oauth_state_service import OAuthStateService
from backend.views.auth import GoogleCallbackView, GoogleLogInView, LogOutView


class GoogleLogInViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_web_login_redirects_to_google_with_web_state(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get("/v1/auth/google/login")
        # Session middleware simulation
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        self.assertIn("state", params)
        state = params["state"][0]

        # Verify decoded state is for web
        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertFalse(decoded["is_mobile"])
        self.assertIsNone(decoded["redirect_url"])
        self.assertEqual(request.session.get("oauth_state"), state)

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_web_login_json_format(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get("/v1/auth/google/login?format=json")
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("authUrl", response.data["data"])
        self.assertIn("state", response.data["data"])

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_mobile_login_via_source_utm(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get(
            "/v1/auth/google/login?sourceUtm=mobile-app&redirectURL=averysync://google-auth"
        )
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        state = params["state"][0]

        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertTrue(decoded["is_mobile"])
        self.assertEqual(decoded["redirect_url"], "averysync://google-auth")

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_mobile_login_via_is_mobile_param(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get(
            "/v1/auth/google/login?is_mobile=true&redirectURL=averysync://google-auth"
        )
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        state = params["state"][0]

        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertTrue(decoded["is_mobile"])

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_mobile_login_via_scheme_auto_detection(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get(
            "/v1/auth/google/login?redirectURL=averysync://google-auth"
        )
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        state = params["state"][0]

        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertTrue(decoded["is_mobile"])
        self.assertEqual(decoded["redirect_url"], "averysync://google-auth")

    @patch("backend.views.auth.GoogleOAuthService.get_authorization_url")
    def test_login_unsafe_redirect_url_ignored(self, mock_auth_url):
        mock_auth_url.side_effect = lambda redirect_url=None, state=None: (
            f"https://accounts.google.com/o/oauth2/v2/auth?state={state}",
            state,
        )

        request = self.factory.get(
            "/v1/auth/google/login?redirectURL=https://evil.example.com"
        )
        request.session = {}

        response = GoogleLogInView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        state = params["state"][0]

        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertIsNone(decoded["redirect_url"])


class GoogleCallbackViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("backend.views.auth.generate_token_pair")
    @patch("backend.views.auth.UserService.create_or_update_user")
    @patch("backend.views.auth.GoogleOAuthService.handle_calback")
    def test_web_callback_success_sets_cookies_and_redirects(
        self, mock_handle_cb, mock_create_user, mock_tokens
    ):
        mock_handle_cb.return_value = {
            "user_id": "google-123",
            "email": "user@example.com",
            "name": "Web User",
            "image": "https://img",
        }
        mock_user = MagicMock(id="user-uuid-1", name="Web User")
        mock_create_user.return_value = mock_user
        mock_tokens.return_value = {
            "access_token": "access_token_xyz",
            "refresh_token": "refresh_token_xyz",
        }

        state = OAuthStateService.generate_state(redirect_url=None, is_mobile=False)

        request = self.factory.get(
            f"/v1/auth/google/callback?code=valid_code&state={state}"
        )
        request.session = {"oauth_state": state}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        # Should redirect to frontend base URL
        frontend = settings.SERVICES.get("FRONTEND", {})
        expected_base = f"{frontend.get('URL', '')}/{frontend.get('REDIRECT_PATH', '')}"
        self.assertTrue(response.url.startswith(expected_base))
        # Ensure tokens are NOT in query string
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        self.assertNotIn("access", params)
        self.assertNotIn("refresh", params)

        # Check cookies
        self.assertIn(
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME"), response.cookies
        )
        self.assertIn(
            settings.COOKIE_SETTINGS.get("REFRESH_TOKEN_COOKIE_NAME"), response.cookies
        )
        access_cookie = response.cookies[
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME")
        ]
        self.assertEqual(access_cookie.value, "access_token_xyz")
        self.assertTrue(access_cookie["httponly"])

    @patch("backend.views.auth.generate_token_pair")
    @patch("backend.views.auth.UserService.create_or_update_user")
    @patch("backend.views.auth.GoogleOAuthService.handle_calback")
    def test_mobile_callback_success_redirects_with_tokens_in_query(
        self, mock_handle_cb, mock_create_user, mock_tokens
    ):
        mock_handle_cb.return_value = {
            "user_id": "google-456",
            "email": "mobile@example.com",
            "name": "Mobile User",
            "image": "https://img",
        }
        mock_user = MagicMock(id="user-uuid-2", name="Mobile User")
        mock_create_user.return_value = mock_user
        mock_tokens.return_value = {
            "access_token": "mobile_access_token_123",
            "refresh_token": "mobile_refresh_token_123",
        }

        mobile_redirect = "averysync://google-auth"
        state = OAuthStateService.generate_state(
            redirect_url=mobile_redirect, is_mobile=True
        )

        request = self.factory.get(
            f"/v1/auth/google/callback?code=valid_code&state={state}"
        )
        request.session = {"oauth_state": state}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith("averysync://google-auth"))
        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)
        self.assertEqual(params.get("access"), ["mobile_access_token_123"])
        self.assertEqual(params.get("refresh"), ["mobile_refresh_token_123"])

    def test_callback_error_param_from_google(self):
        frontend = settings.SERVICES.get("FRONTEND", {})
        expected_base = f"{frontend.get('URL', '')}/{frontend.get('REDIRECT_PATH', '')}"

        request = self.factory.get("/v1/auth/google/callback?error=access_denied")
        request.session = {}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith(expected_base))
        self.assertIn("error=access_denied", response.url)

    def test_callback_missing_code_redirects_with_error(self):
        request = self.factory.get("/v1/auth/google/callback?state=xyz")
        request.session = {}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=missing_code", response.url)

    def test_callback_invalid_state_redirects_with_error(self):
        request = self.factory.get(
            "/v1/auth/google/callback?code=code123&state=tampered_or_invalid"
        )
        request.session = {}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    def test_web_callback_session_mismatch_rejected(self):
        """Vuln #3: Web flow must verify state matches request.session['oauth_state']."""
        state = OAuthStateService.generate_state(redirect_url=None, is_mobile=False)
        request = self.factory.get(
            f"/v1/auth/google/callback?code=code123&state={state}"
        )
        # Session has a different state (or none)
        request.session = {"oauth_state": "other-session-state"}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("error=invalid_state", response.url)

    def test_callback_mobile_error_redirects_to_mobile_deep_link(self):
        mobile_redirect = "averysync://google-auth"
        state = OAuthStateService.generate_state(
            redirect_url=mobile_redirect, is_mobile=True
        )

        request = self.factory.get(
            f"/v1/auth/google/callback?error=user_cancelled&state={state}"
        )
        request.session = {"oauth_state": state}

        response = GoogleCallbackView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response.url.startswith("averysync://google-auth"))
        self.assertIn("error=user_cancelled", response.url)


class LogOutViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_logout_clears_cookies_and_session(self):
        request = self.factory.post("/v1/auth/logout")
        mock_session = MagicMock()
        request.session = mock_session

        response = LogOutView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], ApplicationMessages.GOOGLE_LOGOUT_SUCCESS
        )
        mock_session.flush.assert_called_once()
        self.assertIn(
            settings.COOKIE_SETTINGS.get("ACCESS_TOKEN_COOKIE_NAME"), response.cookies
        )
        self.assertIn(
            settings.COOKIE_SETTINGS.get("REFRESH_TOKEN_COOKIE_NAME"), response.cookies
        )
