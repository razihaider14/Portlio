from fastapi import FastAPI, HTTPException

from app.config import settings
from app.github.client import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
    get_user_repositories,
)

app = FastAPI(title=settings.APP_NAME)


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
    except GitHubUserNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"GitHub user '{username}' not found."
        )
    except GitHubRateLimitError:
        raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded.")
    except GitHubAPIError:
        raise HTTPException(
            status_code=503, detail="GitHub service is temporarily unavailable."
        )

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
