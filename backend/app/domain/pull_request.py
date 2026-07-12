from pydantic import BaseModel, Field, PositiveInt


class PullRequestReference(BaseModel):
    """Normalized identity for a public GitHub pull request."""

    owner: str = Field(description="GitHub repository owner or organization.")
    repository: str = Field(description="GitHub repository name.")
    pull_number: PositiveInt = Field(description="Positive GitHub pull-request number.")
    canonical_url: str = Field(description="Canonical public GitHub pull-request URL.")
