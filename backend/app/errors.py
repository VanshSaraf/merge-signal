INVALID_PULL_REQUEST_URL = "INVALID_PULL_REQUEST_URL"
INVALID_PULL_REQUEST_URL_MESSAGE = "Provide a valid public GitHub pull-request URL."


class InvalidPullRequestUrlError(ValueError):
    """Raised when a value is not a supported public GitHub pull-request URL."""

    code = INVALID_PULL_REQUEST_URL
    message = INVALID_PULL_REQUEST_URL_MESSAGE

    def __init__(self, message: str = INVALID_PULL_REQUEST_URL_MESSAGE) -> None:
        super().__init__(message)
        self.message = message


class ApplicationError(Exception):
    """Base class for safe application errors exposed through the API contract."""

    code = "APPLICATION_ERROR"
    message = "The request could not be completed."

    def __init__(self, message: str | None = None, metadata: dict | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
        self.metadata = metadata or {}


class GitHubPullRequestNotFoundError(ApplicationError):
    code = "GITHUB_PULL_REQUEST_NOT_FOUND"
    message = "The GitHub pull request was not found."


class GitHubRateLimitedError(ApplicationError):
    code = "GITHUB_RATE_LIMITED"
    message = "GitHub rate limit has been reached."


class GitHubAuthenticationFailedError(ApplicationError):
    code = "GITHUB_AUTHENTICATION_FAILED"
    message = "GitHub authentication was rejected."


class GitHubAccessDeniedError(ApplicationError):
    code = "GITHUB_ACCESS_DENIED"
    message = "GitHub access was denied."


class GitHubUnavailableError(ApplicationError):
    code = "GITHUB_UNAVAILABLE"
    message = "GitHub is temporarily unavailable."


class GitHubInvalidResponseError(ApplicationError):
    code = "GITHUB_INVALID_RESPONSE"
    message = "GitHub returned an invalid or unsupported response."


class GitHubPaginationLimitExceededError(ApplicationError):
    code = "GITHUB_PAGINATION_LIMIT_EXCEEDED"
    message = "GitHub pagination could not be completed safely."


class GitHubRequestFailedError(ApplicationError):
    code = "GITHUB_REQUEST_FAILED"
    message = "GitHub request failed."
