import pytest

from app.errors import GitHubPaginationLimitExceededError
from app.integrations.github.pagination import parse_next_link


def test_parse_next_link_returns_safe_next_url() -> None:
    link = '<https://api.github.com/repositories/1/pulls/2/files?page=2>; rel="next"'

    assert (
        parse_next_link(link, "https://api.github.com")
        == "https://api.github.com/repositories/1/pulls/2/files?page=2"
    )


def test_parse_next_link_returns_none_without_next() -> None:
    assert parse_next_link('<https://api.github.com/page=1>; rel="last"', "https://api.github.com") is None
    assert parse_next_link(None, "https://api.github.com") is None


@pytest.mark.parametrize(
    "link",
    [
        '<https://evil.example/repos?page=2>; rel="next"',
        '<http://api.github.com/repos?page=2>; rel="next"',
    ],
)
def test_parse_next_link_rejects_unsafe_urls(link: str) -> None:
    with pytest.raises(GitHubPaginationLimitExceededError):
        parse_next_link(link, "https://api.github.com")


def test_parse_next_link_ignores_malformed_link_without_next_url() -> None:
    assert parse_next_link("not a link", "https://api.github.com") is None
