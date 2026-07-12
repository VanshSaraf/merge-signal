from fastapi import APIRouter
from typing import Annotated

from fastapi import Depends

from app.api.dependencies import get_github_client
from app.integrations.github.client import GitHubRestClient
from app.models.errors import ApiErrorResponse
from app.models.pull_request import (
    FetchPullRequestSnapshotRequest,
    FetchPullRequestSnapshotResponse,
    ParsePullRequestUrlRequest,
    ParsePullRequestUrlResponse,
)
from app.services.pr_url_parser import parse_pull_request_url

router = APIRouter(prefix="/pull-requests", tags=["pull requests"])


@router.post(
    "/parse",
    response_model=ParsePullRequestUrlResponse,
    responses={
        422: {
            "model": ApiErrorResponse,
            "description": "Unsupported or malformed public GitHub pull-request URL.",
        }
    },
)
def parse_pull_request_url_endpoint(
    request: ParsePullRequestUrlRequest,
) -> ParsePullRequestUrlResponse:
    reference = parse_pull_request_url(request.url)
    return ParsePullRequestUrlResponse(data=reference)


@router.post(
    "/snapshot",
    response_model=FetchPullRequestSnapshotResponse,
    responses={
        403: {"model": ApiErrorResponse, "description": "GitHub access denied."},
        404: {"model": ApiErrorResponse, "description": "GitHub pull request not found."},
        429: {"model": ApiErrorResponse, "description": "GitHub rate limit reached."},
        502: {"model": ApiErrorResponse, "description": "GitHub authentication or response failure."},
        503: {"model": ApiErrorResponse, "description": "GitHub temporarily unavailable."},
    },
)
async def fetch_pull_request_snapshot_endpoint(
    request: FetchPullRequestSnapshotRequest,
    github_client: Annotated[GitHubRestClient, Depends(get_github_client)],
) -> FetchPullRequestSnapshotResponse:
    reference = parse_pull_request_url(request.url)
    snapshot = await github_client.get_pull_request_snapshot(reference)
    return FetchPullRequestSnapshotResponse(data=snapshot)
