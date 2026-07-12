from re import IGNORECASE, fullmatch, search
from urllib.parse import unquote, urlparse

from app.domain.pull_request import PullRequestReference
from app.errors import InvalidPullRequestUrlError

_MALFORMED_PERCENT_PATTERN = r"%(?![0-9A-Fa-f]{2})"
_ENCODED_BLOCKLIST_PATTERN = r"%(?:00|2f|5c)"
_PULL_NUMBER_PATTERN = r"[1-9][0-9]*"


def parse_pull_request_url(value: str) -> PullRequestReference:
    """Parse a supported public GitHub pull-request URL without network access."""
    if not isinstance(value, str):
        raise InvalidPullRequestUrlError()

    if not value or value != value.strip() or "\\" in value:
        raise InvalidPullRequestUrlError()

    parsed = urlparse(value)

    if parsed.scheme != "https":
        raise InvalidPullRequestUrlError()

    if parsed.hostname != "github.com":
        raise InvalidPullRequestUrlError()

    if parsed.username is not None or parsed.password is not None:
        raise InvalidPullRequestUrlError()

    try:
        if parsed.port is not None:
            raise InvalidPullRequestUrlError()
    except ValueError as error:
        raise InvalidPullRequestUrlError() from error

    path = parsed.path
    if not path.startswith("/") or search(_MALFORMED_PERCENT_PATTERN, path):
        raise InvalidPullRequestUrlError()

    if search(_ENCODED_BLOCKLIST_PATTERN, path, flags=IGNORECASE):
        raise InvalidPullRequestUrlError()

    normalized_path = path[:-1] if path.endswith("/") else path
    segments = normalized_path.split("/")

    if len(segments) != 5 or segments[0] != "" or segments[3] != "pull":
        raise InvalidPullRequestUrlError()

    owner, repository, pull_number_text = segments[1], segments[2], segments[4]
    decoded_segments = [unquote(segment) for segment in (owner, repository, pull_number_text)]

    if any(
        not segment
        or any(character.isspace() for character in segment)
        or any(character in segment for character in ("/", "\\", "\x00", "%"))
        for segment in decoded_segments
    ):
        raise InvalidPullRequestUrlError()

    if not fullmatch(_PULL_NUMBER_PATTERN, decoded_segments[2]):
        raise InvalidPullRequestUrlError()

    canonical_url = (
        f"https://github.com/{decoded_segments[0]}/{decoded_segments[1]}/pull/{decoded_segments[2]}"
    )

    return PullRequestReference(
        owner=decoded_segments[0],
        repository=decoded_segments[1],
        pull_number=int(decoded_segments[2]),
        canonical_url=canonical_url,
    )
