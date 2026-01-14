from django.http import HttpResponseRedirect
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from backend.services.google_oauth_service import GoogleOAuthService
from rest_framework import status
from django.conf import settings
from backend.services.user_service import UserService
from backend.utils.jwt_utils import generate_token_pair
from backend.constants.messages import ApplicationMessages


class GoogleLogInView(APIView):
    @extend_schema(
        operation_id='google_log_in',
        summary='Google OAuth log in',
        description='Redirects to Google OAuth authorization URL or returns JSON response with auth URL',
        tags=['auth'],
        responses={
            200: OpenApiResponse(description='Generated Google OAuth URL'),
            302: OpenApiResponse(description='Redirect to Google OAuth URL')
        }
    )
    def get(self, request: Request):
        redirect_url = request.query_params.get('redirectURL')
        auth_url, state = GoogleOAuthService.get_authorization_url(redirect_url)
        request.session['oauth_state'] = state

        if request.headers.get('Accept') == "application/json" or request.query_params.get('format') == "json":
            return Response({
                'statusCode': status.HTTP_200_OK,
                'message': 'Google OAuth URL generated',
                'data': {'authUrl': auth_url, 'state': state}
            })
        return HttpResponseRedirect(auth_url)


class GoogleCallbackView(APIView):
    def get(self, request: Request):
        try:
            code = request.query_params.get('code')
            state = request.query_params.get('state')
            error = request.query_params.get('error')

            frontend = settings.SERVICES.get('FRONTEND', {})
            frontend_base_url = f'{frontend.get('URL', '')}/{frontend.get('REDIRECT_PATH', '')}'

            if error:
                return HttpResponseRedirect(f'{frontend_base_url}?error={error}')
            if not code:
                return HttpResponseRedirect(f'{frontend_base_url}?error=missing_code')
            if not state:
                return HttpResponseRedirect(f'{frontend_base_url}?error=missing_state')

            stored_state = request.session.get('oauth_state')
            if not stored_state or stored_state != state:
                return HttpResponseRedirect(f'{frontend_base_url}?error=invalid_state')

            google_user_details = GoogleOAuthService.handle_calback(code)
            user = UserService.create_or_update_user(google_user_details)

            tokens = generate_token_pair(
                {
                    'id': str(user.id),
                    'name': user.name,
                }
            )

            response = HttpResponseRedirect(frontend_base_url)
            
            # TODO: Optimize for mobile log in
            if "averysync://" in frontend_base_url or "exp://" in frontend_base_url:
                query_params = f"?access={tokens['access_token']}&refresh={tokens['refresh_token']}"
                return HttpResponseRedirect(f"{frontend_base_url}{query_params}")
            
            self._set_auth_cookies(response, tokens)
            request.session.pop('oauth_state', None)

            return response
        except Exception as exception:
            return HttpResponseRedirect(f'{frontend_base_url}?error=auth_failed')

    def _get_cookie_config(self):
        return {
            'path': '/',
            'domain': settings.COOKIE_SETTINGS.get('COOKIE_DOMAIN'),
            'httponly': settings.COOKIE_SETTINGS.get('COOKIE_HTTPONLY'),
            'secure': settings.COOKIE_SETTINGS.get('COOKIE_SECURE'),
            'samesite': settings.COOKIE_SETTINGS.get('COOKIE_SAMESITE'),
        }

    def _set_auth_cookies(self, response, tokens):
        config = self._get_cookie_config()

        response.set_cookie(
            settings.COOKIE_SETTINGS.get('ACCESS_TOKEN_COOKIE_NAME'),
            tokens['access_token'],
            max_age=settings.JWT_CONFIG.get('ACCESS_TOKEN_LIFETIME'),
            **config
        )

        response.set_cookie(
            settings.COOKIE_SETTINGS.get('REFRESH_TOKEN_COOKIE_NAME'),
            tokens['refresh_token'],
            max_age=settings.JWT_CONFIG.get('REFRESH_TOKEN_LIFETIME'),
            **config
        )


class LogOutView(APIView):
    def post(self, request: Request):
        request.session.flush()

        response = Response({
            'statusCode': status.HTTP_200_OK,
            'message': ApplicationMessages.GOOGLE_LOGOUT_SUCCESS,
            'data': {'success': True}
        })

        delete_cookies_config = {
            'path': '/',
            'domain': settings.COOKIE_SETTINGS.get('COOKIE_DOMAIN'),
        }
        response.delete_cookie(settings.COOKIE_SETTINGS.get('ACCESS_TOKEN_COOKIE_NAME'), **delete_cookies_config)
        response.delete_cookie(settings.COOKIE_SETTINGS.get('REFRESH_TOKEN_COOKIE_NAME'), **delete_cookies_config)

        delete_session_config = {
            'path': getattr(settings, 'SESSION_COOKIE_PATH', '/'),
            'domain': getattr(settings, 'SESSION_COOKIE_DOMAIN', '/'),
        }

        response.delete_cookie('sessionid', **delete_session_config)

        return response
