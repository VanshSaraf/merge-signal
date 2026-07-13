from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GitHubTransportModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GitHubUser(GitHubTransportModel):
    login: str
    avatar_url: str | None = None
    html_url: str | None = None


class GitHubRepository(GitHubTransportModel):
    full_name: str


class GitHubBranch(GitHubTransportModel):
    ref: str
    sha: str
    repo: GitHubRepository


class GitHubLabel(GitHubTransportModel):
    name: str


class GitHubPullRequest(GitHubTransportModel):
    number: int
    title: str
    body: str | None = None
    state: str
    draft: bool = False
    html_url: str
    user: GitHubUser
    base: GitHubBranch
    head: GitHubBranch
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    additions: int
    deletions: int
    changed_files: int
    commits: int
    mergeable: bool | None = None
    mergeable_state: str | None = None
    labels: list[GitHubLabel] = Field(default_factory=list)


class GitHubPullRequestFile(GitHubTransportModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None
    previous_filename: str | None = None
    blob_url: str | None = None


class GitHubCommitUser(GitHubTransportModel):
    login: str | None = None


class GitHubCommitAuthorDetails(GitHubTransportModel):
    name: str | None = None
    date: datetime | None = None


class GitHubCommitDetails(GitHubTransportModel):
    message: str
    author: GitHubCommitAuthorDetails | None = None
    committer: GitHubCommitAuthorDetails | None = None


class GitHubPullRequestCommit(GitHubTransportModel):
    sha: str
    html_url: str | None = None
    author: GitHubCommitUser | None = None
    commit: GitHubCommitDetails


class GitHubCheckRunApp(GitHubTransportModel):
    name: str | None = None
    slug: str | None = None
    html_url: str | None = None


class GitHubCheckRun(GitHubTransportModel):
    id: int
    name: str
    status: str
    conclusion: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    details_url: str | None = None
    html_url: str | None = None
    external_id: str | None = None
    app: GitHubCheckRunApp | None = None


class GitHubCheckRunsResponse(GitHubTransportModel):
    total_count: int
    check_runs: list[GitHubCheckRun] = Field(default_factory=list)


class GitHubStatusCreator(GitHubTransportModel):
    login: str | None = None
    avatar_url: str | None = None


class GitHubCommitStatus(GitHubTransportModel):
    id: int
    state: str
    context: str
    description: str | None = None
    target_url: str | None = None
    created_at: datetime
    updated_at: datetime
    creator: GitHubStatusCreator | None = None


class GitHubPullRequestReview(GitHubTransportModel):
    id: int
    user: GitHubUser | None = None
    body: str | None = None
    state: str
    html_url: str | None = None
    commit_id: str | None = None
    submitted_at: datetime | None = None


class GitHubPullRequestReviewComment(GitHubTransportModel):
    id: int
    pull_request_review_id: int | None = None
    in_reply_to_id: int | None = None
    user: GitHubUser | None = None
    body: str | None = None
    path: str | None = None
    position: int | None = None
    original_position: int | None = None
    line: int | None = None
    original_line: int | None = None
    start_line: int | None = None
    original_start_line: int | None = None
    side: str | None = None
    start_side: str | None = None
    diff_hunk: str | None = None
    html_url: str | None = None
    commit_id: str | None = None
    original_commit_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
