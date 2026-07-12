import pytest

from app.errors import InvalidPullRequestUrlError
from app.services.pr_url_parser import parse_pull_request_url


@pytest.mark.parametrize(
    ("url", "owner", "repository", "pull_number", "canonical_url"),
    [
        (
            "https://github.com/octocat/Hello-World/pull/1347",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347/",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347?notification_referrer_id=example",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347#discussion_r123",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347?source=test#discussion",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/OwnerName/Repository-Name/pull/999999999",
            "OwnerName",
            "Repository-Name",
            999999999,
            "https://github.com/OwnerName/Repository-Name/pull/999999999",
        ),
        (
            "https://github.com/example-org/service_api.py/pull/42",
            "example-org",
            "service_api.py",
            42,
            "https://github.com/example-org/service_api.py/pull/42",
        ),
        (
            "https://github.com/example-org/service-api/pull/7",
            "example-org",
            "service-api",
            7,
            "https://github.com/example-org/service-api/pull/7",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347?encoded=a%2Fb%5Cc",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
        (
            "https://github.com/octocat/Hello-World/pull/1347#discussion_r123",
            "octocat",
            "Hello-World",
            1347,
            "https://github.com/octocat/Hello-World/pull/1347",
        ),
    ],
)
def test_parse_pull_request_url_accepts_supported_urls(
    url: str,
    owner: str,
    repository: str,
    pull_number: int,
    canonical_url: str,
) -> None:
    reference = parse_pull_request_url(url)

    assert reference.owner == owner
    assert reference.repository == repository
    assert reference.pull_number == pull_number
    assert reference.canonical_url == canonical_url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        " https://github.com/owner/repo/pull/12",
        "https://github.com/owner/repo/pull/12 ",
        "https://github.com/owner/re po/pull/12",
        "github.com/owner/repo/pull/12",
        "//github.com/owner/repo/pull/12",
        "http://github.com/owner/repo/pull/12",
        "ftp://github.com/owner/repo/pull/12",
        "https://gitlab.com/owner/repo/pull/12",
        "https://github.example.com/owner/repo/pull/12",
        "https://api.github.com/owner/repo/pull/12",
        "https://github.com.evil.example/owner/repo/pull/12",
        "https://evilgithub.com/owner/repo/pull/12",
        "https://github.com:443/owner/repo/pull/12",
        "https://github.com:bad/owner/repo/pull/12",
        "https://user@github.com/owner/repo/pull/12",
        "https://user:password@github.com/owner/repo/pull/12",
        "https://github.com/owner/repo",
        "https://github.com/owner/repo/issues/12",
        "https://github.com/owner/repo/commit/abc",
        "https://github.com/owner/repo/compare/main...dev",
        "https://github.com/owner/repo/actions/runs/12",
        "https://github.com//repo/pull/12",
        "https://github.com/owner//pull/12",
        "https://github.com/owner/repo/pull/",
        "https://github.com/owner/repo/pull/0",
        "https://github.com/owner/repo/pull/-1",
        "https://github.com/owner/repo/pull/1.5",
        "https://github.com/owner/repo/pull/abc",
        "https://github.com/owner/repo/pull/+12",
        "https://github.com/owner/repo/pull/12/files",
        "https://github.com/owner/repo/pull/12/commits",
        "https://github.com/owner/repo/pull/12/extra",
        "https://github.com/owner//repo/pull/12",
        "https://github.com/owner%2Frepo/pull/12",
        "https://github.com/owner/repo%2Fpull/12",
        "https://github.com/owner/repo/pull%2F12",
        "https://github.com/owner/repo/pull/12%2Ffiles",
        "https://github.com/owner%252Frepo/pull/12",
        "https://github.com/owner%5Crepo/pull/12",
        "https://github.com/owner\\repo\\pull\\12",
        "https://github.com/owner/repo%ZZ/pull/12",
        "See https://github.com/owner/repo/pull/12",
        "https://github.com/owner/repo/pull/12 please",
        "https://github.com/owner/repo\u2003/pull/12",
        "https://github.com/owner/repo/pull/12%00",
        "https://github.com/" + "a" * 10000,
    ],
)
def test_parse_pull_request_url_rejects_unsupported_urls(url: str) -> None:
    with pytest.raises(InvalidPullRequestUrlError):
        parse_pull_request_url(url)


def test_parse_pull_request_url_rejects_non_string_input() -> None:
    with pytest.raises(InvalidPullRequestUrlError):
        parse_pull_request_url(123)  # type: ignore[arg-type]
