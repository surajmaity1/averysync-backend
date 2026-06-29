from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import SimpleTestCase as TestCase
from django.test import override_settings

from backend.exceptions.auth_exceptions import TokenExpiredError, TokenInvalidError
from backend.utils.jwt_utils import generate_token, validate_token


def _rsa_keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


PRIVATE_KEY, PUBLIC_KEY = _rsa_keypair()

JWT_CONFIG = {
    "ACCESS_TOKEN_LIFETIME": 3600,
    "REFRESH_TOKEN_LIFETIME": 604800,
    "PRIVATE_KEY": PRIVATE_KEY,
    "PUBLIC_KEY": PUBLIC_KEY,
    "ALGORITHM": "RS256",
    "ISSUER": "backend-app-auth",
}


@override_settings(JWT_CONFIG=JWT_CONFIG)
class GenerateAndValidateTokenTests(TestCase):
    def test_round_trip_returns_payload(self):
        token = generate_token({"id": "user-1"}, "Access")

        payload = validate_token(token, "Access")

        self.assertEqual(payload["user_id"], "user-1")
        self.assertEqual(payload["token_type"], "access")
        self.assertEqual(payload["iss"], "backend-app-auth")

    def test_wrong_token_type_rejected(self):
        token = generate_token({"id": "user-1"}, "Access")

        with self.assertRaises(TokenInvalidError):
            validate_token(token, "Refresh")

    def test_expired_token_raises_expired(self):
        issued = datetime.now(timezone.utc) - timedelta(hours=2)
        token = jwt.encode(
            {
                "iss": "backend-app-auth",
                "iat": int(issued.timestamp()),
                "exp": int((issued + timedelta(hours=1)).timestamp()),
                "token_type": "access",
                "sub": "user-1",
                "user_id": "user-1",
            },
            PRIVATE_KEY,
            algorithm="RS256",
        )

        with self.assertRaises(TokenExpiredError):
            validate_token(token, "Access")

    def test_token_with_foreign_issuer_rejected(self):
        token = jwt.encode(
            {
                "iss": "evil-issuer",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                ),
                "token_type": "access",
                "sub": "user-1",
                "user_id": "user-1",
            },
            PRIVATE_KEY,
            algorithm="RS256",
        )

        with self.assertRaises(TokenInvalidError):
            validate_token(token, "Access")

    def test_non_rs256_algorithm_token_rejected(self):
        forged = jwt.encode(
            {
                "iss": "backend-app-auth",
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                ),
                "token_type": "access",
                "user_id": "attacker",
            },
            "attacker-chosen-hmac-secret",
            algorithm="HS256",
        )

        with self.assertRaises(TokenInvalidError):
            validate_token(forged, "Access")

    def test_token_missing_required_claims_rejected(self):
        token = jwt.encode(
            {
                "iss": "backend-app-auth",
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
                ),
                "token_type": "access",
            },
            PRIVATE_KEY,
            algorithm="RS256",
        )

        with self.assertRaises(TokenInvalidError):
            validate_token(token, "Access")
