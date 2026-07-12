from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.integrations.github.client import GitHubRestClient


async def get_github_client() -> AsyncIterator[GitHubRestClient]:
    async with GitHubRestClient(get_settings()) as client:
        yield client
