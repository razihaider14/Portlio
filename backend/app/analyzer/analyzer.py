import asyncio

from app.aggregator.aggregator import aggregate_user_skills
from app.detector.detector import detect_technologies_detailed
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
    Retrieve all public repositories for a user, recursively transverse each repository's full file tree, detect technologies, infer repository metadata, and aggregate everything into a portfolio-level skill report.
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
            response, both of which are always available. Richer
            technology detection also flows through to skill aggregation:
            more/higher-confidence technologies mean richer "skills" and
            "portfolio" fields.

    Returns:
        {
            "username": str,
            "repository_count": int,
            "repositories": [
                {
                    "name": str,
                    "language": str | None,       # GitHub's primary language
                    "contents": [...],             # raw file tree entries
                    "technologies": [str, ...],    # sorted technology names
                    "metadata": {...},              # see analyze_repository_metadata()
                    "skills": [...],                 # this repo's own technologies,
                                                       # scored in isolation as if it
                                                       # were the user's entire
                                                       # portfolio; see
                                                       # aggregate_user_skills()'s
                                                       # "skills" entries for the
                                                       # shape of each element
                },
                ...
            ],
            "portfolio": {...},   # every repository's technologies + metadata
                                    # aggregated together; see
                                    # app.aggregator.aggregator.aggregate_user_skills()
                                    # for the full shape ("skills", "strengths",
                                    # "weaknesses", "recommendations")
        }

    Note:
        Downloaded file content and raw GitHub repository metadata are
        internal analysis details only. Neither is ever included in the
        returned repository objects or the portfolio report; the response
        only ever contains the derived "technologies", "metadata",
        "skills", and "portfolio" fields (all built from
        app.detector/app.metadata/app.aggregator's stable public APIs).
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
    # One aggregator-shaped {"name", "technologies", "metadata"} entry per
    # repository, collected as we go and reused for both this repository's
    # own "skills" field and the portfolio-wide aggregation below, so
    # detection/metadata is never recomputed just to feed the aggregator.
    skill_aggregation_inputs = []
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

        # detect_technologies_detailed() and analyze_repository_metadata()
        # take file_contents/repo_metadata via keys on their input dict.
        # When we have extra context to offer, pass it through a throwaway
        # shallow-copied dict instead of mutating `repository`, so the
        # response object never carries it. This is a cheap shallow copy (a
        # handful of keys; `tree`, `file_contents`, and `repo` are shared by
        # reference, not duplicated), not a copy of the underlying data.
        analysis_input = dict(repository)
        if file_contents:
            analysis_input["file_contents"] = file_contents
        analysis_input["repo_metadata"] = repo

        # detect_technologies_detailed() is the detector's richer form
        # (MatchResult objects with category/confidence); the stable
        # "technologies" list is derived from it rather than calling
        # detect_technologies() separately, so detection only runs once
        # per repository. This keeps "technologies" byte-for-byte
        # identical to before skill aggregation existed.
        technologies_detailed = detect_technologies_detailed(analysis_input)
        repository["technologies"] = sorted(
            match.name for match in technologies_detailed
        )
        repository["metadata"] = analyze_repository_metadata(analysis_input)

        # MatchResult objects never leave this function: they're only ever
        # handed to the aggregator (which knows how to read them) or used
        # to build the plain "technologies" list above.
        skill_input = {
            "name": repository["name"],
            "technologies": technologies_detailed,
            "metadata": repository["metadata"],
        }
        skill_aggregation_inputs.append(skill_input)

        # This repository's own technologies, aggregated in isolation (as
        # if it were the user's entire portfolio). aggregate_user_skills()
        # already returns a stable, JSON-safe dict, so its "skills" list
        # can be attached directly.
        repository["skills"] = aggregate_user_skills([skill_input])["skills"]

        repositories.append(repository)

    # Portfolio-level skill report: every repository's technologies and
    # metadata aggregated together across the whole portfolio.
    portfolio = aggregate_user_skills(skill_aggregation_inputs)

    return {
        "username": github_username,
        "repository_count": len(repositories),
        "repositories": repositories,
        "portfolio": portfolio,
    }
