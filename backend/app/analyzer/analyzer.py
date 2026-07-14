import asyncio

from app.detector.detector import detect_technologies
from app.github.client import (
    get_repository_file_contents,
    get_repository_tree,
    get_user_repositories,
)
from app.metadata.metadata_analyzer import analyze_repository_metadata


async def analyze_user_repositories(
    username: str, include_content: bool = False
) -> dict:
    """
    Retrieve all public repositories for a user, recursively transverse each repository's full file tree, detect technologies, and infer repository metadata.
    Repositories that are empty (no commits) will have an empty contents and technologies list.

    Args:
        username: GitHub username to analyze.
        include_content: If True, also download the content of files useful
            for content-based detection and metadata analysis
            (requirements.txt, package.json, README.md, LICENSE, etc.;
            see app.github.content_targets) and use it internally to
            improve technology detection (HasFileContent, HasDependency,
            ...) and metadata analysis (README structure, license text
            matching, ...). This costs one extra GitHub API request per
            useful file found, so it's opt-in rather than the default.
            Metadata analysis still runs and returns useful results without
            it, most fields (project type, tests, CI/CD, Docker, package
            managers, build systems, license via the GitHub API, maturity,
            size metrics) only need the tree and the GitHub repo API
            response, both of which are always available.

    Note:
        Downloaded file content and raw GitHub repository metadata are
        internal analysis details only. Neither is ever included in the
        returned repository objects, the response only ever contains the
        derived "technologies" and "metadata" fields.
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
        # This is what gets returned to the API caller. file_contents and
        # the raw GitHub repo object are deliberately never attached here,
        # they're internal inputs to analysis, not part of the public
        # response shape.
        repository = {
            "name": repo["name"],
            "language": repo.get("language"),
            "contents": tree,
        }

        # detect_technologies() and analyze_repository_metadata() take
        # file_contents/repo_metadata via keys on their input dict. When we
        # have extra context to offer, pass it through a throwaway
        # shallow-copied dict instead of mutating `repository`, so the
        # response object never carries it. This is a cheap shallow copy (a
        # handful of keys; `tree`, `file_contents`, and `repo` are shared by
        # reference, not duplicated), not a copy of the underlying data.
        analysis_input = dict(repository)
        if file_contents:
            analysis_input["file_contents"] = file_contents
        analysis_input["repo_metadata"] = repo

        repository["technologies"] = detect_technologies(analysis_input)
        repository["metadata"] = analyze_repository_metadata(analysis_input)
        repositories.append(repository)

    return {
        "username": github_username,
        "repository_count": len(repositories),
        "repositories": repositories,
    }
