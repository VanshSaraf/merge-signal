from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictDomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PullRequestReference(StrictDomainModel):
    """Normalized identity for a public GitHub pull request."""

    owner: str = Field(description="GitHub repository owner or organization.")
    repository: str = Field(description="GitHub repository name.")
    pull_number: PositiveInt = Field(description="Positive GitHub pull-request number.")
    canonical_url: str = Field(description="Canonical public GitHub pull-request URL.")


class PullRequestAuthor(StrictDomainModel):
    login: str = Field(description="GitHub user login.")
    avatar_url: str | None = Field(description="GitHub avatar URL when available.")
    html_url: str | None = Field(description="GitHub profile URL when available.")


class PullRequestBranch(StrictDomainModel):
    ref: str = Field(description="Branch ref.")
    sha: str = Field(description="Branch commit SHA.")
    repository_full_name: str = Field(description="Repository full name for the branch.")


class PullRequestMetadata(StrictDomainModel):
    number: int = Field(description="Pull-request number.")
    title: str = Field(description="Pull-request title.")
    body: str | None = Field(description="Pull-request body.")
    state: str = Field(description="Pull-request state.")
    draft: bool = Field(description="Whether the pull request is a draft.")
    html_url: str = Field(description="GitHub pull-request URL.")
    author: PullRequestAuthor = Field(description="Pull-request author.")
    base_branch: PullRequestBranch = Field(description="Base branch.")
    head_branch: PullRequestBranch = Field(description="Head branch.")
    head_sha: str = Field(description="Head commit SHA.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")
    closed_at: datetime | None = Field(description="Close timestamp when available.")
    merged_at: datetime | None = Field(description="Merge timestamp when available.")
    additions: int = Field(description="Total additions reported by GitHub.")
    deletions: int = Field(description="Total deletions reported by GitHub.")
    changed_files: int = Field(description="Changed-file count reported by GitHub.")
    commit_count: int = Field(description="Commit count reported by GitHub.")
    mergeable: bool | None = Field(description="GitHub mergeable value when computed.")
    mergeable_state: str | None = Field(description="GitHub mergeable state when available.")
    labels: list[str] = Field(description="Pull-request label names.")


class ChangedFile(StrictDomainModel):
    filename: str = Field(description="Changed file path.")
    status: str = Field(description="GitHub file status.")
    additions: int = Field(description="Line additions.")
    deletions: int = Field(description="Line deletions.")
    changes: int = Field(description="Total line changes.")
    patch: str | None = Field(description="Patch text when GitHub provides it.")
    previous_filename: str | None = Field(description="Previous path for renamed files.")
    blob_url: str | None = Field(description="GitHub blob URL when available.")


class PullRequestCommit(StrictDomainModel):
    sha: str = Field(description="Commit SHA.")
    message: str = Field(description="Commit message.")
    html_url: str | None = Field(description="GitHub commit URL when available.")
    author_login: str | None = Field(description="Linked GitHub author login when available.")
    author_name: str | None = Field(description="Commit author name when available.")
    authored_at: datetime | None = Field(description="Authored timestamp when available.")
    committed_at: datetime | None = Field(description="Committed timestamp when available.")


class GitHubRateLimit(StrictDomainModel):
    limit: int | None = Field(description="GitHub rate limit when available.")
    remaining: int | None = Field(description="Remaining GitHub requests when available.")
    used: int | None = Field(description="Used GitHub requests when available.")
    resource: str | None = Field(description="GitHub rate-limit resource when available.")
    reset_at: datetime | None = Field(description="Rate-limit reset time when available.")


class SnapshotCompleteness(StrictDomainModel):
    files_complete: bool = Field(description="Whether changed-file retrieval is complete.")
    commits_complete: bool = Field(description="Whether commit retrieval is complete.")
    missing_patch_count: int = Field(description="Number of changed files without patches.")
    warnings: list[str] = Field(description="Completeness and partial-data warnings.")


class PullRequestSnapshot(StrictDomainModel):
    reference: PullRequestReference = Field(description="Normalized pull-request reference.")
    metadata: PullRequestMetadata = Field(description="Normalized pull-request metadata.")
    files: list[ChangedFile] = Field(description="Changed files in GitHub order.")
    commits: list[PullRequestCommit] = Field(description="Commits in GitHub order.")
    completeness: SnapshotCompleteness = Field(description="Snapshot completeness details.")
    fetched_at: datetime = Field(description="UTC timestamp when snapshot was fetched.")
    rate_limit: GitHubRateLimit = Field(description="Latest available GitHub rate-limit metadata.")
