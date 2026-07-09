import asyncio

from app.detector.detector import detect_technologies
from app.github.client import (
    get_repository_file_contents,
    get_repository_tree,
    get_user_repositories,
)


async def analyze_user_repositories(
    username: str, include_content: bool = False
) -> dict:
    """
    Retrieve all public repositories for a user, recursively transverse each repository's full file tree, and detect technologies.
    Repositories that are empty (no commits) will have an empty contents and technologies list.

    Args:
        username: GitHub username to analyze.
        include_content: If True, also download the content of files useful
            for content-based detection (requirements.txt, package.json,
            etc.; see app.github.content_targets) and use it internally to
            improve technology detection via content-based matchers
            (HasFileContent, HasDependency, ...). This costs one extra
            GitHub API request per useful file found, so it's opt-in rather
            than the default.

    Note:
        Downloaded file content is an internal detection detail only. It is
        never included in the returned repository objects, regardless of
        include_content, the response shape is identical either way except
        for the "technologies" list.
    """
    repos = await get_user_repositories(username)

    github_username = repos[0]["owner"]["login"] if repos else username

    trees = await asyncio.gather(
        *[get_repository_tree(github_username, repo["name"]) for repo in repos]
    )

    if include_content:
        file_content_maps = await asyncio.gather(
            *[
                get_repository_file_contents(github_username, repo["name"], tree)
                for repo, tree in zip(repos, trees)
            ]
        )
    else:
        file_content_maps = [{} for _ in repos]

    repositories = []
    for repo, tree, file_contents in zip(repos, trees, file_content_maps):
        # This is what gets returned to the API caller. file_contents is
        # deliberately never attached here as it's an internal detail of
        # detection, not part of the public response shape.
        repository = {
            "name": repo["name"],
            "language": repo.get("language"),
            "contents": tree,
        }

        # detect_technologies() takes file_contents via a "file_contents"
        # key on its input dict (see app.detector.detector). When we have
        # content to offer, pass it through a throwaway shallow-copied dict
        # instead of mutating `repository`, so the response object never
        # carries it. This is a cheap shallow copy (a handful of keys,
        # `tree` and `file_contents` are shared by reference, not
        # duplicated), not a copy of the underlying data.
        detection_input = (
            {**repository, "file_contents": file_contents}
            if file_contents
            else repository
        )
        repository["technologies"] = detect_technologies(detection_input)
        repositories.append(repository)

    return {
        "username": github_username,
        "repository_count": len(repositories),
        "repositories": repositories,
    }
