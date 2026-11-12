from django.test import SimpleTestCase, override_settings

from backend.exceptions.auth_exceptions import AuthException
from backend.services.oauth_state_service import OAuthStateService


class GenerateAndDecodeStateTests(SimpleTestCase):
    def test_generate_state_and_decode_roundtrip(self):
        redirect_url = "averysync://auth/callback"
        state = OAuthStateService.generate_state(
            redirect_url=redirect_url, is_mobile=True
        )
        self.assertIsInstance(state, str)
        self.assertTrue(len(state) > 0)

        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertEqual(decoded["redirect_url"], redirect_url)
        self.assertTrue(decoded["is_mobile"])
        self.assertIn("nonce", decoded)

    def test_generate_state_web_defaults(self):
        state = OAuthStateService.generate_state(redirect_url=None, is_mobile=False)
        decoded = OAuthStateService.verify_and_decode_state(state)
        self.assertIsNone(decoded["redirect_url"])
        self.assertFalse(decoded["is_mobile"])

    def test_verify_and_decode_state_tampered_raises_auth_exception(self):
        state = OAuthStateService.generate_state(
            redirect_url="averysync://auth/callback", is_mobile=True
        )
        tampered_state = state[:-4] + "xxxx"
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(tampered_state)

    def test_verify_and_decode_state_expired_raises_auth_exception(self):
        state = OAuthStateService.generate_state(
            redirect_url="averysync://auth/callback", is_mobile=True
        )
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(state, max_age=-1)


class StateSaltTests(SimpleTestCase):
    """Vuln #4: signing.dumps must use a dedicated salt so that a payload signed
    elsewhere with the same SECRET_KEY but no salt cannot verify as OAuth state."""

    def test_state_uses_dedicated_salt(self):
        """A state generated with salt must fail verification without salt."""
        from django.core import signing

        # Generate a real state via the service (uses salt)
        state = OAuthStateService.generate_state(redirect_url=None, is_mobile=False)

        # Try to decode it without salt — must fail
        with self.assertRaises(Exception):
            signing.loads(state)  # no salt → BadSignature

    def test_unsalted_payload_rejected_as_state(self):
        """A payload signed without salt must NOT verify as OAuth state."""
        from django.core import signing

        fake_payload = signing.dumps(
            {"redirect_url": None, "is_mobile": False, "nonce": "fake"}
        )
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(fake_payload)


class StateNonceSingleUseTests(SimpleTestCase):
    """Vuln #3a: The nonce must be consumed on first use so the state
    cannot be replayed within the max_age window."""

    def test_state_is_single_use(self):
        state = OAuthStateService.generate_state(redirect_url=None, is_mobile=False)

        # First use succeeds
        OAuthStateService.verify_and_decode_state(state)

        # Second use must fail — nonce already consumed
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(state)


class VerifyAndDecodeStateBadInputTests(SimpleTestCase):
    """Vuln #6: verify_and_decode_state must raise AuthException for None,
    empty, or non-string input — not crash with TypeError."""

    def test_none_input_raises_auth_exception(self):
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(None)

    def test_empty_string_raises_auth_exception(self):
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state("")

    def test_integer_input_raises_auth_exception(self):
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state(12345)

    def test_dict_input_raises_auth_exception(self):
        with self.assertRaises(AuthException):
            OAuthStateService.verify_and_decode_state({"bad": "input"})


class IsSafeRedirectUrlUserinfoBypassTests(SimpleTestCase):
    """Vuln #1: Host check must NOT be bypassable via userinfo (@) in netloc."""

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["localhost", "127.0.0.1"],
        DEBUG=True,
    )
    def test_rejects_userinfo_bypass_at_sign(self):
        """https://localhost:x@evil.com/ must be rejected."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://localhost:x@evil.com/")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["localhost", "127.0.0.1"],
        DEBUG=True,
    )
    def test_rejects_userinfo_bypass_with_port(self):
        """https://localhost:3000@evil.com/ must be rejected."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://localhost:3000@evil.com/")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["localhost", "127.0.0.1"],
        DEBUG=True,
    )
    def test_rejects_backslash_at_variant(self):
        """https://evil.com\\@localhost must be rejected."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://evil.com\\@localhost")
        )


class IsSafeRedirectUrlSchemeTests(SimpleTestCase):
    """Vuln #2: Custom schemes must be checked against exact URIs,
    not just the scheme name. exp:// must only work in DEBUG mode."""

    @override_settings(
        ALLOWED_NATIVE_REDIRECT_URIS=["averysync://auth/callback"],
        DEBUG=False,
    )
    def test_exact_native_uri_accepted(self):
        self.assertTrue(
            OAuthStateService.is_safe_redirect_url("averysync://auth/callback")
        )

    @override_settings(
        ALLOWED_NATIVE_REDIRECT_URIS=["averysync://auth/callback"],
        DEBUG=False,
    )
    def test_arbitrary_native_host_rejected(self):
        """averysync://anything should be rejected if not in exact list."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("averysync://evil.com/steal")
        )

    @override_settings(
        ALLOWED_NATIVE_REDIRECT_URIS=["averysync://auth/callback"],
        DEBUG=False,
    )
    def test_exp_scheme_rejected_in_production(self):
        """exp:// must NOT be allowed when DEBUG=False."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("exp://192.168.1.5:8081/--/cb")
        )

    @override_settings(
        ALLOWED_NATIVE_REDIRECT_URIS=["averysync://auth/callback"],
        DEBUG=True,
    )
    def test_exp_scheme_allowed_in_debug(self):
        """exp:// is allowed when DEBUG=True (Expo Go dev mode)."""
        self.assertTrue(
            OAuthStateService.is_safe_redirect_url("exp://192.168.1.5:8081/--/cb")
        )

    @override_settings(
        ALLOWED_NATIVE_REDIRECT_URIS=["averysync://auth/callback"],
        DEBUG=False,
    )
    def test_arbitrary_scheme_with_attacker_host_rejected(self):
        """exp://attacker.com/... must be rejected in production."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("exp://attacker.com/steal")
        )


class IsSafeRedirectUrlHttpsEnforcementTests(SimpleTestCase):
    """Vuln #5: http:// must be rejected when DEBUG=False (production)."""

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["app.averysync.com"],
        DEBUG=False,
    )
    def test_http_rejected_in_production(self):
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("http://app.averysync.com/feed")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["app.averysync.com"],
        DEBUG=False,
    )
    def test_https_accepted_in_production(self):
        self.assertTrue(
            OAuthStateService.is_safe_redirect_url("https://app.averysync.com/feed")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["localhost"],
        DEBUG=True,
    )
    def test_http_accepted_in_debug(self):
        self.assertTrue(
            OAuthStateService.is_safe_redirect_url("http://localhost:3000/feed")
        )


class IsSafeRedirectUrlInsecureDefaultsTests(SimpleTestCase):
    """Vuln #5: A missing ALLOWED_REDIRECT_HOSTS setting must NOT
    silently fall back to localhost / 127.0.0.1."""

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=[],
        SERVICES={"FRONTEND": {"URL": "https://app.averysync.com"}},
        DEBUG=False,
    )
    def test_empty_hosts_does_not_allow_localhost(self):
        """With empty ALLOWED_REDIRECT_HOSTS, localhost must NOT be allowed."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://localhost:3000/feed")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=[],
        SERVICES={"FRONTEND": {"URL": "https://app.averysync.com"}},
        DEBUG=False,
    )
    def test_empty_hosts_does_not_allow_127(self):
        """With empty ALLOWED_REDIRECT_HOSTS, 127.0.0.1 must NOT be allowed."""
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://127.0.0.1:3000/feed")
        )


class IsSafeRedirectUrlWebHostsTests(SimpleTestCase):
    """General tests for web host validation using url_has_allowed_host_and_scheme."""

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["app.averysync.com", "localhost:3000"],
        DEBUG=True,
    )
    def test_allowed_host_accepted(self):
        self.assertTrue(
            OAuthStateService.is_safe_redirect_url("http://app.averysync.com/feed")
        )

    @override_settings(
        ALLOWED_REDIRECT_HOSTS=["app.averysync.com"],
        DEBUG=True,
    )
    def test_disallowed_host_rejected(self):
        self.assertFalse(
            OAuthStateService.is_safe_redirect_url("https://malicious.example.com/")
        )

    def test_javascript_scheme_rejected(self):
        self.assertFalse(OAuthStateService.is_safe_redirect_url("javascript:alert(1)"))

    def test_empty_string_rejected(self):
        self.assertFalse(OAuthStateService.is_safe_redirect_url(""))

    def test_none_rejected(self):
        self.assertFalse(OAuthStateService.is_safe_redirect_url(None))


class BuildRedirectUrlTests(SimpleTestCase):
    def test_merges_params(self):
        url = OAuthStateService.build_redirect_url(
            "averysync://auth/callback",
            {"access": "token_a", "refresh": "token_b"},
        )
        self.assertIn("access=token_a", url)
        self.assertIn("refresh=token_b", url)

    def test_preserves_existing_query_params(self):
        url = OAuthStateService.build_redirect_url(
            "averysync://auth/callback?flow=signin",
            {"access": "token_a"},
        )
        self.assertIn("flow=signin", url)
        self.assertIn("access=token_a", url)

    def test_server_params_override_client_params(self):
        url = OAuthStateService.build_redirect_url(
            "averysync://auth/callback?access=old_value",
            {"access": "new_value"},
        )
        self.assertIn("access=new_value", url)
        self.assertNotIn("access=old_value", url)

    def test_preserves_blank_values(self):
        """Smaller issue: parse_qsl should use keep_blank_values=True."""
        url = OAuthStateService.build_redirect_url(
            "averysync://auth/callback?a=",
            {"b": "val"},
        )
        self.assertIn("a=", url)
        self.assertIn("b=val", url)
