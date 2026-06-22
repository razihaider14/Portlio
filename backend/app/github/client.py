import httpx

from app.config import settings

BASE_URL = "https://api.github.com"
GITHUB_TIMEOUT = 10.0


class GitHubUserNotFoundError(Exception):
    """Raised when the requested GitHub user doesn't exist."""


class GitHubRateLimitError(Exception):
    """Raised when the GitHub API rate limit has been exceeded."""


class GitHubAPIError(Exception):
    """Raised when GitHun returns an unexpected error response."""


def _build_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SkillForge-App",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


async def get_user_repositories(username: str) -> list[dict]:
    """
    Fetch the public repositories of a GitHub user.
    Raises:
    GitHubUserNotFoundError: if the user does not exist (404)
    GitHubRateLimitError: if the rate limit has been exceeded (403)
    GitHubAPIError: for any other unexpected error response.
    """
    url = f"{BASE_URL}/users/{username}/repos"

    async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
        response = await client.get(
            url,
            params={"per_page": 100},
            headers=_build_headers(),
        )

    if response.status_code == 404:
        raise GitHubUserNotFoundError(username)

    if response.status_code == 403:
        data = response.json()

        if "rate limit" in data.get("message", "").lower():
            raise GitHubRateLimitError()

        raise GitHubAPIError(data.get("message", "Forbidden"))

    if response.is_error:
        raise GitHubAPIError(f"GitHub API returned {response.status_code}")

    return response.json()
