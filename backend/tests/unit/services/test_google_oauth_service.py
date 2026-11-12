from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import requests
from django.test import override_settings
from django.test import SimpleTestCase as TestCase

from backend.constants.messages import ApiErrors
from backend.exceptions.auth_exceptions import APIException, AuthException
from backend.services.google_oauth_service import GoogleOAuthService

GOOGLE_OAUTH = {
    "CLIENT_ID": "client-id",
    "CLIENT_SECRET": "client-secret",
    "REDIRECT_URI": "https://app.example.com/callback",
    "ALLOWED_REDIRECT_URIS": [
        "https://app.example.com/callback",
        "https://other.example.com/cb",
    ],
}


def fake_response(status_code=200, json_data=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    return response


@override_settings(GOOGLE_OAUTH=GOOGLE_OAUTH)
class GetAuthorizationUrlTests(TestCase):
    def test_builds_url_with_expected_params_and_state(self):
        url, state = GoogleOAuthService.get_authorization_url()

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertTrue(url.startswith(GoogleOAuthService.GOOGLE_AUTH_URL))
        self.assertEqual(params["client_id"], ["client-id"])
        self.assertEqual(params["redirect_uri"], [GOOGLE_OAUTH["REDIRECT_URI"]])
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["scope"], ["openid email profile"])
        self.assertEqual(params["state"], [state])
        self.assertTrue(state)

    def test_generates_unique_state_per_call(self):
        _, state_one = GoogleOAuthService.get_authorization_url()
        _, state_two = GoogleOAuthService.get_authorization_url()

        self.assertNotEqual(state_one, state_two)

    def test_allowlisted_redirect_url_overrides_default(self):
        custom = "https://other.example.com/cb"

        url, _ = GoogleOAuthService.get_authorization_url(redirect_url=custom)

        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["redirect_uri"], [custom])

    def test_unlisted_redirect_url_falls_back_to_default(self):
        url, _ = GoogleOAuthService.get_authorization_url(
            redirect_url="https://evil.example.com/steal"
        )

        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["redirect_uri"], [GOOGLE_OAUTH["REDIRECT_URI"]])

    def test_uses_provided_state_when_given(self):
        custom_state = "my-custom-signed-state"
        url, state = GoogleOAuthService.get_authorization_url(state=custom_state)

        params = parse_qs(urlparse(url).query)
        self.assertEqual(state, custom_state)
        self.assertEqual(params["state"], [custom_state])

    @patch("backend.services.google_oauth_service.secrets.token_urlsafe")
    def test_failure_raises_auth_exception(self, mock_token):
        mock_token.side_effect = RuntimeError("no entropy")

        with self.assertRaises(AuthException):
            GoogleOAuthService.get_authorization_url()


@override_settings(GOOGLE_OAUTH=GOOGLE_OAUTH)
class ExchangeCodeForTokensTests(TestCase):
    @patch("backend.services.google_oauth_service.requests.post")
    def test_returns_tokens_on_success(self, mock_post):
        mock_post.return_value = fake_response(json_data={"access_token": "abc"})

        tokens = GoogleOAuthService._exchange_code_for_tokens("auth-code")

        self.assertEqual(tokens, {"access_token": "abc"})
        sent = mock_post.call_args
        self.assertEqual(sent.args[0], GoogleOAuthService.GOOGLE_TOKEN_URL)
        self.assertEqual(sent.kwargs["data"]["code"], "auth-code")
        self.assertEqual(sent.kwargs["timeout"], 30)

    @patch("backend.services.google_oauth_service.requests.post")
    def test_non_200_raises_api_exception(self, mock_post):
        mock_post.return_value = fake_response(status_code=400)

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService._exchange_code_for_tokens("auth-code")

        self.assertEqual(str(ctx.exception), ApiErrors.EXCHANGE_AUTH_CODE_FAILED)

    @patch("backend.services.google_oauth_service.requests.post")
    def test_error_field_in_body_raises_api_exception(self, mock_post):
        mock_post.return_value = fake_response(json_data={"error": "invalid_grant"})

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService._exchange_code_for_tokens("auth-code")

        self.assertEqual(str(ctx.exception), ApiErrors.GOOGLE_API_ERROR)

    @patch("backend.services.google_oauth_service.requests.post")
    def test_request_exception_raises_api_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError()

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService._exchange_code_for_tokens("auth-code")

        self.assertEqual(str(ctx.exception), ApiErrors.GOOGLE_API_ERROR)


class FetchUserDetailsTests(TestCase):
    @patch("backend.services.google_oauth_service.requests.get")
    def test_returns_user_details_on_success(self, mock_get):
        details = {"id": "1", "email": "u@example.com", "name": "U"}
        mock_get.return_value = fake_response(json_data=details)

        result = GoogleOAuthService._fetch_user_details("access-token")

        self.assertEqual(result, details)
        sent = mock_get.call_args
        self.assertEqual(sent.args[0], GoogleOAuthService.GOOGLE_USER_INFO_URL)
        self.assertEqual(
            sent.kwargs["headers"], {"Authorization": "Bearer access-token"}
        )

    @patch("backend.services.google_oauth_service.requests.get")
    def test_non_200_raises_api_exception(self, mock_get):
        mock_get.return_value = fake_response(status_code=401)

        with self.assertRaises(APIException):
            GoogleOAuthService._fetch_user_details("access-token")

    @patch("backend.services.google_oauth_service.requests.get")
    def test_missing_required_fields_raises_api_exception(self, mock_get):
        mock_get.return_value = fake_response(json_data={"id": "1"})

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService._fetch_user_details("access-token")

        # Both missing fields are reported.
        self.assertIn("email", str(ctx.exception))
        self.assertIn("name", str(ctx.exception))

    @patch("backend.services.google_oauth_service.requests.get")
    def test_request_exception_raises_api_exception(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService._fetch_user_details("access-token")

        self.assertEqual(str(ctx.exception), ApiErrors.GOOGLE_API_ERROR)


class HandleCallbackTests(TestCase):
    @patch.object(GoogleOAuthService, "_fetch_user_details")
    @patch.object(GoogleOAuthService, "_exchange_code_for_tokens")
    def test_returns_normalized_user_payload(self, mock_exchange, mock_fetch):
        mock_exchange.return_value = {"access_token": "token-123"}
        mock_fetch.return_value = {
            "id": "google-1",
            "email": "u@example.com",
            "name": "User",
            "picture": "https://example.com/p.png",
        }

        result = GoogleOAuthService.handle_calback("auth-code")

        self.assertEqual(
            result,
            {
                "user_id": "google-1",
                "email": "u@example.com",
                "name": "User",
                "image": "https://example.com/p.png",
            },
        )
        mock_exchange.assert_called_once_with("auth-code")
        mock_fetch.assert_called_once_with("token-123")

    @patch.object(GoogleOAuthService, "_fetch_user_details")
    @patch.object(GoogleOAuthService, "_exchange_code_for_tokens")
    def test_missing_picture_defaults_to_none(self, mock_exchange, mock_fetch):
        mock_exchange.return_value = {"access_token": "token-123"}
        mock_fetch.return_value = {
            "id": "google-1",
            "email": "u@example.com",
            "name": "User",
        }

        result = GoogleOAuthService.handle_calback("auth-code")

        self.assertIsNone(result["image"])

    @patch.object(GoogleOAuthService, "_exchange_code_for_tokens")
    def test_api_exception_propagates_unchanged(self, mock_exchange):
        original = APIException(ApiErrors.EXCHANGE_AUTH_CODE_FAILED)
        mock_exchange.side_effect = original

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService.handle_calback("auth-code")

        self.assertIs(ctx.exception, original)

    @patch.object(GoogleOAuthService, "_fetch_user_details")
    @patch.object(GoogleOAuthService, "_exchange_code_for_tokens")
    def test_unexpected_error_wrapped_in_api_exception(self, mock_exchange, mock_fetch):
        mock_exchange.return_value = {"access_token": "token-123"}
        mock_fetch.side_effect = KeyError("boom")

        with self.assertRaises(APIException) as ctx:
            GoogleOAuthService.handle_calback("auth-code")

        self.assertEqual(str(ctx.exception), ApiErrors.GOOGLE_API_ERROR)
