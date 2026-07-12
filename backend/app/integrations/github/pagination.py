from urllib.parse import urlparse

from app.errors import GitHubPaginationLimitExceededError


def parse_next_link(link_header: str | None, api_base_url: str) -> str | None:
    """Return a safe GitHub rel=next URL from a Link header."""
    if not link_header:
        return None

    for raw_part in link_header.split(","):
        part = raw_part.strip()
        if not part.startswith("<") or ">;" not in part:
            continue

        url_part, metadata_part = part.split(">;", 1)
        url = url_part[1:]
        rel_values = [item.strip() for item in metadata_part.split(";")]
        if 'rel="next"' not in rel_values:
            continue

        _ensure_safe_next_url(url, api_base_url)
        return url

    return None


def _ensure_safe_next_url(url: str, api_base_url: str) -> None:
    parsed = urlparse(url)
    base = urlparse(api_base_url)

    if parsed.scheme != base.scheme or parsed.netloc != base.netloc or not parsed.path.startswith("/"):
        raise GitHubPaginationLimitExceededError()
