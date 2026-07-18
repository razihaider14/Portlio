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
                    "name": str,           # e.g. "Django", or "ESP32" for a
                                            # derived/composite skill
                    "category": str,
                    "repository_count": int,
                    "repositories": [str, ...],
                    "average_detector_confidence": float,
                    "average_practice_score": float,
                    "score": int,
                    "max_score": int,
                    "tier": "expert" | "proficient" | "developing" | "exposure",
                    "evidence": [str, ...],
                    "is_composite": bool,  # True for derived skills like
                                            # "ESP32"/"IoT"/"Embedded Systems"
                },
                ...
            ],                      # every detected skill (including derived
                                     # composites), score descending
            "strengths": [...],     # subset of "skills" tiered "proficient"/"expert"
            "weaknesses": [
                {
                    "kind": "shallow_skill" | "limited_practice" | "limited_breadth",
                    "name": str,           # a skill name for "shallow_skill";
                                            # a human-readable label (e.g.
                                            # "CI/CD", "Frontend Breadth")
                                            # otherwise
                    "category": str | None,  # None for "limited_practice"
                    "description": str,
                    "evidence": [str, ...],
                },
                ...
            ],                      # NOT the same shape as "skills"; see
                                     # app.aggregator.models.WeaknessKind
            "recommendations": [
                {
                    "skill": str,
                    "category": str,
                    "reason": str,
                    "based_on": [str, ...],  # established root skill(s)
                    "chain": [str, ...],     # hypothetical intermediate
                                              # skill(s), e.g. ["FreeRTOS"]
                                              # for an "ESP-IDF" recommendation
                                              # reached via established
                                              # "ESP32" -> "FreeRTOS" ->
                                              # "ESP-IDF"; empty for a direct,
                                              # 1-hop recommendation
                },
                ...
            ],
        }
        See app.aggregator.aggregator.aggregate_user_skills() for the
        authoritative, field-by-field definition of this shape.
    """
    try:
        analysis = await analyze_user_repositories(
            username, include_content=include_content
        )
    except (GitHubUserNotFoundError, GitHubRateLimitError, GitHubAPIError) as exc:
        _handle_github_exceptions(exc)

    return analysis["portfolio"]
