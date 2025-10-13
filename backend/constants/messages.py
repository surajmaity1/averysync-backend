class ApiErrors:
    GOOGLE_AUTH_FAILED = 'Google authentication failed'
    EXCHANGE_AUTH_CODE_FAILED = 'Exchange authorization code failed'
    GOOGLE_API_ERROR = 'Google API error'
    USER_DETAILS_FETCH_FAILED = 'Fetching user details failed: {0}'
    MISSING_USER_DETAILS_FIELDS = 'Missing user details fields: {0}'


class ValidationErrors:
    GOOGLE_ID_REQUIRED = 'Google Id required'
    EMAIL_REQUIRED = 'Email Id required'
    NAME_REQUIRED = 'Name Id required'
    IMAGE_REQUIRED = 'Image Id required'