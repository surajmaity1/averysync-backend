import secrets
from urllib.parse import urlencode

from django.conf import settings

from backend.constants.messages import ApiErrors
from backend.exceptions.auth_exceptions import AuthException, APIException
import requests


class GoogleOAuthService:
    GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USER_INFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'

    @classmethod
    def get_authorization_url(cls, redirect_url: str | None = None) -> tuple[str, str]:
        try:
            state = secrets.token_urlsafe(32)

            params = {
                'client_id': settings.GOOGLE_OAUTH['CLIENT_ID'],
                'redirect_uri': redirect_url or settings.GOOGLE_OAUTH['REDIRECT_URI'],
                'response_type': 'code',
                'scope': 'openid email profile',
                'access_type': 'offline',
                'prompt': 'consent',
                'state': state
            }

            auth_url = f'{cls.GOOGLE_AUTH_URL}?{urlencode(params)}'
            return auth_url, state
        except Exception:
            raise AuthException(ApiErrors.GOOGLE_AUTH_FAILED)
    

    @classmethod
    def _exchange_code_for_tokens(cls, authorization_code: str) -> dict:
        try:
            data = {
                'client_id': settings.GOOGLE_OAUTH['CLIENT_ID'],
                'client_secret': settings.GOOGLE_OAUTH['CLIENT_SECRET'],
                'code': authorization_code,
                'grant_type': 'authorization_code',
                'redirect_uri': settings.GOOGLE_OAUTH['REDIRECT_URI'],
            }

            response = requests.post(cls.GOOGLE_TOKEN_URL, data=data, timeout=30)

            if response.status_code != 200:
                raise APIException(ApiErrors.EXCHANGE_AUTH_CODE_FAILED)
            
            tokens = response.json()

            if 'error' in tokens:
                raise APIException(ApiErrors.GOOGLE_API_ERROR)
            
            return tokens
        except requests.exceptions.RequestException:
            raise APIException(ApiErrors.GOOGLE_API_ERROR)


    @classmethod
    def _fetch_user_details(cls, access_token: str) -> dict:
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(cls.GOOGLE_USER_INFO_URL, headers=headers, timeout=30)

            if response.status_code != 200:
                raise APIException(ApiErrors.USER_DETAILS_FETCH_FAILED.format('HTTP Error'))
            
            user_details = response.json()
            required_fields = ['id', 'email', 'name']
            missing_fields = [field for field in required_fields if field not in user_details]

            if missing_fields:
                raise APIException(ApiErrors.MISSING_USER_DETAILS_FIELDS.format(', '.join(missing_fields)))
            
            return user_details
        except requests.exceptions.RequestException:
            raise APIException(ApiErrors.GOOGLE_API_ERROR)





    @classmethod
    def handle_calback(cls, authorization_code: str) -> dict:
        try:
            tokens = cls._exchange_code_for_tokens(authorization_code)
            user_details = cls._fetch_user_details(tokens)

            return {
                'user_id': user_details['id'],
                'email': user_details['email'],
                'name': user_details['name'],
                'image': user_details.get('image'),
            }
        except Exception as exception:
            if isinstance(exception, APIException):
                raise
            raise APIException(ApiErrors.GOOGLE_API_ERROR) from exception

