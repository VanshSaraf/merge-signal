import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import Settings
from app.domain.pull_request import (
    CheckRunRecord,
    ChangedFile,
    CommitStatusRecord,
    GitHubRateLimit,
    PullRequestAuthor,
    PullRequestBranch,
    PullRequestCommit,
    PullRequestCi,
    PullRequestMetadata,
    PullRequestReference,
    PullRequestReviewRecord,
    PullRequestSnapshot,
    ReviewCommentRecord,
    ReviewContext,
    SnapshotCompleteness,
)
from app.errors import (
    GitHubAccessDeniedError,
    GitHubAuthenticationFailedError,
    GitHubInvalidResponseError,
    GitHubPaginationLimitExceededError,
    GitHubPullRequestNotFoundError,
    GitHubRateLimitedError,
    GitHubRequestFailedError,
    GitHubUnavailableError,
)
from app.integrations.github.models import (
    GitHubCheckRun,
    GitHubCheckRunsResponse,
    GitHubCommitStatus,
    GitHubPullRequest,
    GitHubPullRequestCommit,
    GitHubPullRequestFile,
    GitHubPullRequestReview,
    GitHubPullRequestReviewComment,
)
from app.integrations.github.pagination import parse_next_link
from app.file_priority import calculate_file_priorities
from app.readiness import calculate_merge_readiness
from app.review_actions import build_review_actions
from app.scoring import calculate_evidence_confidence, calculate_merge_risk
from app.services.ci_explanation import build_ci_explanation
from app.services.ci_state import aggregate_ci_state
from app.services.file_classifier import classify_changed_files
from app.services.review_context import (
    build_review_context,
    normalize_review_state,
    safe_github_url,
    sanitize_review_body,
)
from app.signals.engine import analyze_snapshot_signals

SleepCallable = Callable[[float], Awaitable[None]]


class GitHubRestClient:
    """Asynchronous data-access client for public GitHub pull-request data."""

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
        sleep: SleepCallable = asyncio.sleep,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._sleep = sleep
        self._base_url = settings.github_api_base_url_string
        self._latest_rate_limit = GitHubRateLimit(
            limit=None,
            remaining=None,
            used=None,
            resource=None,
            reset_at=None,
        )
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=settings.github_request_timeout_seconds,
            headers=self._headers(),
        )

    async def __aenter__(self) -> "GitHubRestClient":
        return self

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_pull_request(self, reference: PullRequestReference) -> PullRequestMetadata:
        path = self._repo_path(reference, "pulls", str(reference.pull_number))
        payload = await self._request_json("GET", path)
        upstream = self._validate_payload(payload, GitHubPullRequest)
        return self._normalize_pull_request(upstream)

    async def list_pull_request_files(self, reference: PullRequestReference) -> list[ChangedFile]:
        path = self._repo_path(reference, "pulls", str(reference.pull_number), "files")
        items = await self._request_paginated(path)
        return [
            self._normalize_file(self._validate_payload(item, GitHubPullRequestFile))
            for item in items
        ]

    async def list_pull_request_commits(
        self,
        reference: PullRequestReference,
    ) -> list[PullRequestCommit]:
        path = self._repo_path(reference, "pulls", str(reference.pull_number), "commits")
        items = await self._request_paginated(path)
        return [
            self._normalize_commit(self._validate_payload(item, GitHubPullRequestCommit))
            for item in items
        ]

    async def list_check_runs(
        self,
        reference: PullRequestReference,
        head_sha: str,
    ) -> tuple[list[CheckRunRecord], int, int]:
        path = self._repo_path(reference, "commits", head_sha, "check-runs")
        items, total_count, pages_fetched = await self._request_paginated_collection(
            path,
            "check_runs",
            total_count_key="total_count",
        )
        return (
            [
                self._normalize_check_run(self._validate_payload(item, GitHubCheckRun))
                for item in items
            ],
            total_count if total_count is not None else len(items),
            pages_fetched,
        )

    async def list_commit_statuses(
        self,
        reference: PullRequestReference,
        head_sha: str,
    ) -> tuple[list[CommitStatusRecord], int]:
        path = self._repo_path(reference, "statuses", head_sha)
        items, pages_fetched = await self._request_paginated_with_pages(path)
        return (
            [
                self._normalize_commit_status(self._validate_payload(item, GitHubCommitStatus))
                for item in items
            ],
            pages_fetched,
        )

    async def list_pull_request_reviews(
        self,
        reference: PullRequestReference,
    ) -> tuple[list[PullRequestReviewRecord], int]:
        path = self._repo_path(reference, "pulls", str(reference.pull_number), "reviews")
        items, pages_fetched = await self._request_paginated_with_pages(path)
        return (
            [
                self._normalize_review(self._validate_payload(item, GitHubPullRequestReview))
                for item in items
            ],
            pages_fetched,
        )

    async def list_pull_request_review_comments(
        self,
        reference: PullRequestReference,
    ) -> tuple[list[ReviewCommentRecord], int]:
        path = self._repo_path(reference, "pulls", str(reference.pull_number), "comments")
        items, pages_fetched = await self._request_paginated_with_pages(path)
        return (
            [
                self._normalize_review_comment(self._validate_payload(item, GitHubPullRequestReviewComment))
                for item in items
            ],
            pages_fetched,
        )

    async def get_pull_request_review_context(
        self,
        reference: PullRequestReference,
        *,
        pr_author_login: str | None = None,
        head_sha: str | None = None,
    ) -> ReviewContext:
        warnings: list[str] = []
        reviews: list[PullRequestReviewRecord] = []
        comments: list[ReviewCommentRecord] = []
        review_pages_fetched = 0
        comment_pages_fetched = 0
        reviews_complete = True
        comments_complete = True

        try:
            reviews, review_pages_fetched = await self.list_pull_request_reviews(reference)
        except (
            GitHubAccessDeniedError,
            GitHubUnavailableError,
            GitHubInvalidResponseError,
            GitHubPaginationLimitExceededError,
        ):
            reviews_complete = False
            warnings.append("Pull-request reviews could not be retrieved from GitHub.")

        try:
            comments, comment_pages_fetched = await self.list_pull_request_review_comments(reference)
        except (
            GitHubAccessDeniedError,
            GitHubUnavailableError,
            GitHubInvalidResponseError,
            GitHubPaginationLimitExceededError,
        ):
            comments_complete = False
            warnings.append("Inline review comments could not be retrieved from GitHub.")

        return build_review_context(
            reviews,
            comments,
            reviews_complete=reviews_complete,
            comments_complete=comments_complete,
            review_pages_fetched=review_pages_fetched,
            comment_pages_fetched=comment_pages_fetched,
            pr_author_login=pr_author_login,
            head_sha=head_sha,
            warnings=warnings,
        )

    async def get_pull_request_ci(
        self,
        reference: PullRequestReference,
        head_sha: str,
    ) -> PullRequestCi:
        warnings: list[str] = []
        check_runs: list[CheckRunRecord] = []
        statuses: list[CommitStatusRecord] = []
        total_check_runs: int | None = None
        check_run_pages_fetched = 0
        status_pages_fetched = 0
        check_runs_complete = True
        statuses_complete = True

        try:
            check_runs, total_check_runs, check_run_pages_fetched = await self.list_check_runs(
                reference,
                head_sha,
            )
            if total_check_runs != len(check_runs):
                check_runs_complete = False
                warnings.append("GitHub reported more check runs than were retrieved.")
        except (
            GitHubAccessDeniedError,
            GitHubUnavailableError,
            GitHubInvalidResponseError,
            GitHubPaginationLimitExceededError,
        ):
            check_runs_complete = False
            warnings.append("Check runs could not be retrieved from GitHub.")

        try:
            statuses, status_pages_fetched = await self.list_commit_statuses(reference, head_sha)
        except (
            GitHubAccessDeniedError,
            GitHubUnavailableError,
            GitHubInvalidResponseError,
            GitHubPaginationLimitExceededError,
        ):
            statuses_complete = False
            warnings.append("Commit statuses could not be retrieved from GitHub.")

        return aggregate_ci_state(
            check_runs,
            statuses,
            check_runs_complete=check_runs_complete,
            commit_statuses_complete=statuses_complete,
            check_run_pages_fetched=check_run_pages_fetched,
            commit_status_pages_fetched=status_pages_fetched,
            total_check_runs=total_check_runs,
            warnings=warnings,
            rate_limit=self._latest_rate_limit,
        )

    async def get_pull_request_snapshot(
        self,
        reference: PullRequestReference,
    ) -> PullRequestSnapshot:
        metadata = await self.get_pull_request(reference)
        files = await self.list_pull_request_files(reference)
        files, classification_summary = classify_changed_files(files)
        commits = await self.list_pull_request_commits(reference)
        ci = await self.get_pull_request_ci(reference, metadata.head_sha)
        ci_explanation = build_ci_explanation(ci)
        review_context = await self.get_pull_request_review_context(
            reference,
            pr_author_login=metadata.author.login,
            head_sha=metadata.head_sha,
        )
        completeness = self._build_completeness(metadata, files, commits)

        snapshot = PullRequestSnapshot(
            reference=reference,
            metadata=metadata,
            files=files,
            commits=commits,
            ci=ci,
            ci_explanation=ci_explanation,
            review_context=review_context,
            classification_summary=classification_summary,
            completeness=completeness,
            fetched_at=datetime.now(UTC),
            rate_limit=self._latest_rate_limit,
        )
        signal_result = analyze_snapshot_signals(snapshot)
        scored_snapshot = snapshot.model_copy(
            update={
                "signals": signal_result.signals,
                "signal_summary": signal_result.summary,
            }
        )
        scored_snapshot = scored_snapshot.model_copy(
            update={
                "merge_risk": calculate_merge_risk(signal_result.signals),
                "evidence_confidence": calculate_evidence_confidence(scored_snapshot),
            }
        )
        scored_snapshot = scored_snapshot.model_copy(
            update={
                "merge_readiness": calculate_merge_readiness(scored_snapshot),
            }
        )
        ranked_files, file_priority_summary = calculate_file_priorities(scored_snapshot)
        scored_snapshot = scored_snapshot.model_copy(
            update={
                "ranked_files": ranked_files,
                "file_priority_summary": file_priority_summary,
            }
        )
        review_actions, review_action_summary = build_review_actions(scored_snapshot)
        return scored_snapshot.model_copy(
            update={
                "review_actions": review_actions,
                "review_action_summary": review_action_summary,
            }
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self._settings.github_user_agent,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = self._settings.github_token_value
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _repo_path(self, reference: PullRequestReference, *segments: str) -> str:
        encoded = [
            "repos",
            quote(reference.owner, safe=""),
            quote(reference.repository, safe=""),
            *(quote(segment, safe="") for segment in segments),
        ]
        return "/" + "/".join(encoded)

    async def _request_paginated(self, path: str) -> list[dict[str, Any]]:
        items, _pages_fetched = await self._request_paginated_with_pages(path)
        return items

    async def _request_paginated_with_pages(self, path: str) -> tuple[list[dict[str, Any]], int]:
        items: list[dict[str, Any]] = []
        next_url: str | None = path
        seen_urls: set[str] = set()
        page = 1
        pages_fetched = 0

        while next_url:
            if page > self._settings.github_max_pages or next_url in seen_urls:
                raise GitHubPaginationLimitExceededError()
            seen_urls.add(next_url)

            response = await self._request(
                "GET",
                next_url,
                params={"per_page": self._settings.github_per_page, "page": page}
                if next_url == path
                else None,
            )
            payload = self._parse_json(response)
            if not isinstance(payload, list):
                raise GitHubInvalidResponseError()

            pages_fetched += 1
            items.extend(payload)
            next_url = parse_next_link(response.headers.get("Link"), self._base_url)
            if next_url is None and len(payload) < self._settings.github_per_page:
                break
            page += 1

        return items, pages_fetched

    async def _request_paginated_collection(
        self,
        path: str,
        item_key: str,
        total_count_key: str,
    ) -> tuple[list[dict[str, Any]], int | None, int]:
        items: list[dict[str, Any]] = []
        total_count: int | None = None
        next_url: str | None = path
        seen_urls: set[str] = set()
        page = 1
        pages_fetched = 0

        while next_url:
            if page > self._settings.github_max_pages or next_url in seen_urls:
                raise GitHubPaginationLimitExceededError()
            seen_urls.add(next_url)

            response = await self._request(
                "GET",
                next_url,
                params={"per_page": self._settings.github_per_page, "page": page}
                if next_url == path
                else None,
            )
            payload = self._parse_json(response)
            if not isinstance(payload, dict) or not isinstance(payload.get(item_key), list):
                raise GitHubInvalidResponseError()
            if total_count_key in payload:
                if not isinstance(payload[total_count_key], int):
                    raise GitHubInvalidResponseError()
                total_count = payload[total_count_key]

            page_items = payload[item_key]
            pages_fetched += 1
            items.extend(page_items)
            next_url = parse_next_link(response.headers.get("Link"), self._base_url)
            if next_url is None and len(page_items) < self._settings.github_per_page:
                break
            page += 1

        return items, total_count, pages_fetched

    async def _request_json(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(method, url, params=params)
        payload = self._parse_json(response)
        if not isinstance(payload, dict):
            raise GitHubInvalidResponseError()
        return payload

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        attempts = self._settings.github_max_retries + 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                response = await self._client.request(method, url, params=params)
                self._latest_rate_limit = extract_rate_limit(response.headers)
                if response.status_code in {502, 503, 504}:
                    if attempt < attempts - 1:
                        await self._sleep(self._settings.github_retry_base_delay_seconds * (2**attempt))
                        continue
                    raise GitHubUnavailableError()
                if response.status_code >= 400:
                    self._raise_for_status(response)
                return response
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = error
                if attempt < attempts - 1:
                    await self._sleep(self._settings.github_retry_base_delay_seconds * (2**attempt))
                    continue
                raise GitHubUnavailableError() from error

        raise GitHubUnavailableError() from last_error

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise GitHubAuthenticationFailedError()
        if response.status_code == 404:
            raise GitHubPullRequestNotFoundError()
        if response.status_code == 429 or self._is_rate_limited(response):
            metadata = {}
            if self._latest_rate_limit.reset_at is not None:
                metadata["reset_at"] = self._latest_rate_limit.reset_at.isoformat()
            raise GitHubRateLimitedError(metadata=metadata)
        if response.status_code == 403:
            raise GitHubAccessDeniedError()
        if response.status_code >= 500:
            raise GitHubRequestFailedError()
        raise GitHubRequestFailedError()

    def _is_rate_limited(self, response: httpx.Response) -> bool:
        if response.headers.get("X-RateLimit-Remaining") == "0":
            return True
        try:
            payload = response.json()
        except ValueError:
            return False
        message = str(payload.get("message", "")).lower() if isinstance(payload, dict) else ""
        return "rate limit" in message

    def _parse_json(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as error:
            raise GitHubInvalidResponseError() from error

    def _validate_payload(self, payload: Any, model_type: type) -> Any:
        try:
            return TypeAdapter(model_type).validate_python(payload)
        except ValidationError as error:
            raise GitHubInvalidResponseError() from error

    def _normalize_pull_request(self, upstream: GitHubPullRequest) -> PullRequestMetadata:
        return PullRequestMetadata(
            number=upstream.number,
            title=upstream.title,
            body=upstream.body,
            state=upstream.state,
            draft=upstream.draft,
            html_url=upstream.html_url,
            author=PullRequestAuthor(
                login=upstream.user.login,
                avatar_url=upstream.user.avatar_url,
                html_url=upstream.user.html_url,
            ),
            base_branch=PullRequestBranch(
                ref=upstream.base.ref,
                sha=upstream.base.sha,
                repository_full_name=upstream.base.repo.full_name,
            ),
            head_branch=PullRequestBranch(
                ref=upstream.head.ref,
                sha=upstream.head.sha,
                repository_full_name=upstream.head.repo.full_name,
            ),
            head_sha=upstream.head.sha,
            created_at=upstream.created_at,
            updated_at=upstream.updated_at,
            closed_at=upstream.closed_at,
            merged_at=upstream.merged_at,
            additions=upstream.additions,
            deletions=upstream.deletions,
            changed_files=upstream.changed_files,
            commit_count=upstream.commits,
            mergeable=upstream.mergeable,
            mergeable_state=upstream.mergeable_state,
            labels=[label.name for label in upstream.labels],
        )

    def _normalize_file(self, upstream: GitHubPullRequestFile) -> ChangedFile:
        return ChangedFile(
            filename=upstream.filename,
            status=upstream.status,
            additions=upstream.additions,
            deletions=upstream.deletions,
            changes=upstream.changes,
            patch=upstream.patch,
            previous_filename=upstream.previous_filename,
            blob_url=upstream.blob_url,
        )

    def _normalize_commit(self, upstream: GitHubPullRequestCommit) -> PullRequestCommit:
        return PullRequestCommit(
            sha=upstream.sha,
            message=upstream.commit.message,
            html_url=upstream.html_url,
            author_login=upstream.author.login if upstream.author else None,
            author_name=upstream.commit.author.name if upstream.commit.author else None,
            authored_at=upstream.commit.author.date if upstream.commit.author else None,
            committed_at=upstream.commit.committer.date if upstream.commit.committer else None,
        )

    def _normalize_check_run(self, upstream: GitHubCheckRun) -> CheckRunRecord:
        return CheckRunRecord(
            id=upstream.id,
            name=upstream.name,
            status=upstream.status,
            conclusion=upstream.conclusion,
            provider_name=upstream.app.name if upstream.app else None,
            provider_slug=upstream.app.slug if upstream.app else None,
            details_url=upstream.details_url,
            started_at=upstream.started_at,
            completed_at=upstream.completed_at,
        )

    def _normalize_commit_status(self, upstream: GitHubCommitStatus) -> CommitStatusRecord:
        return CommitStatusRecord(
            id=upstream.id,
            context=upstream.context,
            state=upstream.state,
            description=upstream.description,
            target_url=upstream.target_url,
            creator_login=upstream.creator.login if upstream.creator else None,
            created_at=upstream.created_at,
            updated_at=upstream.updated_at,
        )

    def _normalize_review(self, upstream: GitHubPullRequestReview) -> PullRequestReviewRecord:
        return PullRequestReviewRecord(
            id=upstream.id,
            reviewer_login=upstream.user.login if upstream.user else "unknown",
            state=normalize_review_state(upstream.state),
            submitted_at=upstream.submitted_at,
            body_excerpt=sanitize_review_body(upstream.body),
            html_url=safe_github_url(upstream.html_url),
            commit_sha=upstream.commit_id,
        )

    def _normalize_review_comment(self, upstream: GitHubPullRequestReviewComment) -> ReviewCommentRecord:
        return ReviewCommentRecord(
            id=upstream.id,
            reviewer_login=upstream.user.login if upstream.user else "unknown",
            body_excerpt=sanitize_review_body(upstream.body) or "",
            created_at=upstream.created_at,
            updated_at=upstream.updated_at,
            html_url=safe_github_url(upstream.html_url),
            pull_request_review_id=upstream.pull_request_review_id,
            in_reply_to_id=upstream.in_reply_to_id,
            path=upstream.path,
            line=upstream.line,
            start_line=upstream.start_line,
            side=upstream.side,
            start_side=upstream.start_side,
            current_position=upstream.position,
            original_position=upstream.original_position,
            commit_sha=upstream.commit_id,
        )

    def _build_completeness(
        self,
        metadata: PullRequestMetadata,
        files: list[ChangedFile],
        commits: list[PullRequestCommit],
    ) -> SnapshotCompleteness:
        warnings: list[str] = []
        missing_patch_count = sum(1 for file in files if file.patch is None)
        if missing_patch_count:
            warnings.append("One or more changed files do not include patch data from GitHub.")

        files_complete = len(files) == metadata.changed_files
        commits_complete = len(commits) == metadata.commit_count
        if not files_complete:
            warnings.append("GitHub reported more changed files than were retrieved.")
        if not commits_complete:
            warnings.append("GitHub reported a different commit count than was retrieved.")

        return SnapshotCompleteness(
            files_complete=files_complete,
            commits_complete=commits_complete,
            missing_patch_count=missing_patch_count,
            warnings=warnings,
        )


def extract_rate_limit(headers: httpx.Headers) -> GitHubRateLimit:
    return GitHubRateLimit(
        limit=_parse_optional_int(headers.get("X-RateLimit-Limit")),
        remaining=_parse_optional_int(headers.get("X-RateLimit-Remaining")),
        used=_parse_optional_int(headers.get("X-RateLimit-Used")),
        resource=headers.get("X-RateLimit-Resource"),
        reset_at=_parse_reset_at(headers.get("X-RateLimit-Reset")),
    )


def _parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_reset_at(value: str | None) -> datetime | None:
    parsed = _parse_optional_int(value)
    if parsed is None:
        return None
    try:
        return datetime.fromtimestamp(parsed, UTC)
    except (OverflowError, OSError, ValueError):
        return None
