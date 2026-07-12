from pydantic import BaseModel, ConfigDict, Field, StrictStr

from app.domain.pull_request import PullRequestReference, PullRequestSnapshot


class ParsePullRequestUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: StrictStr = Field(description="Public GitHub pull-request URL to parse.")


class ParsePullRequestUrlResponse(BaseModel):
    data: PullRequestReference = Field(description="Normalized pull-request reference.")


class FetchPullRequestSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: StrictStr = Field(description="Public GitHub pull-request URL to fetch.")


class FetchPullRequestSnapshotResponse(BaseModel):
    data: PullRequestSnapshot = Field(description="Normalized pull-request snapshot.")
