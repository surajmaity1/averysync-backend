class ApiErrors:
    GOOGLE_AUTH_FAILED = 'Google authentication failed'
    EXCHANGE_AUTH_CODE_FAILED = 'Exchange authorization code failed'
    GOOGLE_API_ERROR = 'Google API error'
    USER_DETAILS_FETCH_FAILED = 'Fetching user details failed: {0}'
    MISSING_USER_DETAILS_FIELDS = 'Missing user details fields: {0}'
    USER_NOT_FOUND = 'User not found with id: {0}'
    UNEXPECTED_ERROR_OCCURRED = 'Unexpected error occurred'
    INTERNAL_SERVER_ERROR = 'Internal server error'
    AUTHENTICATION_FAILED = 'Authentication failed: {0}'
    VALIDATION_ERROR = 'Validation error'
    REPOSITORY_ERROR = 'Repository error'
    POST_NOT_FOUND_WITH_ID = 'Post not found with id {0}'
    POST_NOT_FOUND = 'Post not found'
    


class ValidationErrors:
    GOOGLE_ID_REQUIRED = 'Google Id required'
    EMAIL_REQUIRED = 'Email Id required'
    NAME_REQUIRED = 'Name Id required'
    IMAGE_REQUIRED = 'Image Id required'
    TITLE_REQUIRED = 'Title required'


class RepositoryError:
    USER_CREATE_UPDATE_FAILED = 'User create/update failed: {0}'
    USER_NOT_FOUND = 'User not found: {0}'
    POST_CREATION_FAILED = 'Failed to create post: {0}'
    POST_FETCH_FAILED = 'Failed to fetch post: {0}'


class AuthErrorMessages:
    TOKEN_INVALID = 'Invalid token'
    TOKEN_EXPIRED = 'Token expired'
    REFRESH_TOKEN_EXPIRED = 'Refresh token expired, try login again'
    AUTHENTICATION_REQUIRED = 'Authentication required'
    ACCESS_TOKEN_MISSING = 'Access token missing'


class ApplicationMessages:
    GOOGLE_LOGOUT_SUCCESS = 'Logged out successfully from Google'
    POST_CREATED = 'Post created successfully'
