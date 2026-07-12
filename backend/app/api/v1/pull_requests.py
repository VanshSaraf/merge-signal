from fastapi import APIRouter

from app.models.errors import ApiErrorResponse
from app.models.pull_request import ParsePullRequestUrlRequest, ParsePullRequestUrlResponse
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
