import asyncio

from app.github.client import get_repository_contents, get_user_repositories


async def analyze_user_repositories(username: str) -> dict:
    """
    Retrieve all public repositories for a user and return their root directory contents
    Repositories that are empty (no commits) will have an empty contents list.
    """
    repos = await get_user_repositories(username)

    github_username = repos[0]["owner"]["login"] if repos else username

    contents = await asyncio.gather(
        *[get_repository_contents(github_username, repo["name"]) for repo in repos]
    )

    repositories = [
        {
            "name": repo["name"],
            "language": repo.get("language"),
            "contents": [
                {
                    "name": entry["name"],
                    "type": entry["type"],
                }
                for entry in repo_contents
            ],
        }
        for repo, repo_contents in zip(repos, contents)
    ]

    return {
        "username": github_username,
        "repository_count": len(repositories),
        "repositories": repositories,
    }
