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
