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
async def analyze_github_user(username: str, include_content: bool = False):
    try:
        return await analyze_user_repositories(
            username, include_content=include_content
        )
    except (GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError) as exc:
        _handle_github_exceptions(exc)


@app.get("/skills/{username}")
async def get_user_skills(username: str, include_content: bool = False):
    """
    Return only the portfolio-level skill report for a GitHub user: every
    repository is analyzed exactly as in GET /analyze/{username}, but the
    response contains just the aggregated result, not the per-repository
    detail.

    Args:
        username: GitHub username to analyze.
        include_content: Same meaning as on GET /analyze/{username}: opt
            into downloading manifest/README content for richer technology
            detection and metadata analysis, which in turn feeds richer
            skill aggregation.

    Returns:
        {
            "repository_count": int,
            "skills": [
                {
                    "name": str,
                    "category": str,
                    "repository_count": int,
                    "repositories": [str, ...],
                    "average_detector_confidence": float,
                    "average_practice_score": float,
                    "score": int,
                    "max_score": int,
                    "tier": "expert" | "proficient" | "developing" | "exposure",
                    "evidence": [str, ...],
                },
                ...
            ],                      # every detected skill, score descending
            "strengths": [...],     # subset of "skills" tiered "proficient"/"expert"
            "weaknesses": [...],    # subset of "skills" tiered "exposure"
            "recommendations": [
                {
                    "skill": str,
                    "category": str,
                    "reason": str,
                    "based_on": [str, ...],
                },
                ...
            ],
        }
        See app.aggregator.aggregator.aggregate_user_skills() for the
        authoritative definition of this shape.
    """
    try:
        analysis = await analyze_user_repositories(
            username, include_content=include_content
        )
    except (GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError) as exc:
        _handle_github_exceptions(exc)

    return analysis["portfolio"]
