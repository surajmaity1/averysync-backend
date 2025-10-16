from backend.constants.messages import ApiErrors, RepositoryError


class BaseAuthException(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(self.msg)


class AuthException(BaseAuthException):
    def __init__(self, msg: str = ApiErrors.GOOGLE_AUTH_FAILED):
        super().__init__(msg)


class APIException(BaseAuthException):
    def __init__(self, msg: str = ApiErrors.GOOGLE_API_ERROR):
        super().__init__(msg)


class UserNotFoundException(BaseAuthException):
    def __init__(self, msg: str = RepositoryError.USER_NOT_FOUND):
        super().__init__(msg)
