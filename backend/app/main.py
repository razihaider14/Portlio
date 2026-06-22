from fastapi import FastAPI, HTTPException

from app.analyzer.analyzer import analyze_user_repositories
from app.config import settings
from app.github.client import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
    get_user_repositories,
)

app = FastAPI(title=settings.APP_NAME)


def _handle_github_exceptions(exc: Exception) -> None:
    """Convert GitHub client exceptions into FastAPI HTTP responses."""
    if isinstance(exc, GitHubUserNotFoundError):
        raise HTTPException(status_code=404, detail="GitHub user not found.")
    if isinstance(exc, GitHubRateLimitError):
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded.")
    if isinstance(exc, GitHubAPIError):
        raise HTTPException(
            status_code=503, detail="GitHub service is temporarily unavailable."
        )


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.APP_NAME}"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/github/{username}")
async def get_github_user_repos(username: str):
    try:
        repos = await get_user_repositories(username)
    except (GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError) as exc:
        _handle_github_exceptions(exc)

    github_username = repos[0]["owner"]["login"] if repos else username

    repositories = sorted(
        [
            {
                "name": repo.get("name"),
                "description": repo.get("description"),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count"),
                "forks": repo.get("forks_count"),
                "url": repo.get("html_url"),
            }
            for repo in repos
        ],
        key=lambda repo: repo["stars"],
        reverse=True,
    )

    return {
        "username": github_username,
        "repository_count": len(repositories),
        "repositories": repositories,
    }


@app.get("/analyze/{username}")
async def analyze_github_user(username: str):
    try:
        return await analyze_user_repositories(username)
    except (GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError) as exc:
        _handle_github_exceptions(exc)
