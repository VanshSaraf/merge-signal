from pydantic import BaseModel, ConfigDict, Field, StrictStr

from app.domain.pull_request import PullRequestReference


class ParsePullRequestUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: StrictStr = Field(description="Public GitHub pull-request URL to parse.")


class ParsePullRequestUrlResponse(BaseModel):
    data: PullRequestReference = Field(description="Normalized pull-request reference.")
