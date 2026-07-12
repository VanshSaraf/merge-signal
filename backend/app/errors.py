INVALID_PULL_REQUEST_URL = "INVALID_PULL_REQUEST_URL"
INVALID_PULL_REQUEST_URL_MESSAGE = "Provide a valid public GitHub pull-request URL."


class InvalidPullRequestUrlError(ValueError):
    """Raised when a value is not a supported public GitHub pull-request URL."""

    code = INVALID_PULL_REQUEST_URL
    message = INVALID_PULL_REQUEST_URL_MESSAGE

    def __init__(self, message: str = INVALID_PULL_REQUEST_URL_MESSAGE) -> None:
        super().__init__(message)
        self.message = message
