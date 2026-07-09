import asyncio
import base64
import binascii

import httpx

from app.config import settings
from app.github.content_targets import CONTENT_TARGET_FILENAMES, select_content_targets

BASE_URL = "https://api.github.com"
GITHUB_TIMEOUT = 10.0

_TREE_TYPE_MAP = {"blob": "file", "tree": "dir"}


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


def _handle_error_response(response: httpx.Response) -> None:
    """Raise the appropriate exception for a non-2xx GitHub response."""
    if response.status_code == 403:
        data = response.json()
        if "rate limit" in data.get("message", "").lower():
            raise GitHubRateLimitError()
        raise GitHubAPIError(data.get("message", "Forbidden"))

    if response.is_error:
        raise GitHubAPIError(f"GitHub API returned {response.status_code}")


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

    _handle_error_response(response)
    return response.json()


async def get_repository_tree(owner: str, repo: str) -> list[dict]:
    """
    Fetch the complete file tree of a repo in a single API call using Git Trees API with recursive = 1.
    Each returned entry contains:
    "path": full relative path from the repo root (e.g "src/main.py")
    "name": the final path component (e.g "main.py")
    "type": "file" (blob) or "dir" (tree)
    Returns an empty list if the repository is empty (no commits yet).
    If GitHub truncates the tree (> 100,000 entries), the partial result is returned as-is.
    Raises:
    GitHubRateLimitError: if the rate limit has been exceeded (403).
    GitHubAPIError: for any other unexpected error response.
    """
    url = f"{BASE_URL}/repos/{owner}/{repo}/git/trees/HEAD"

    async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
        response = await client.get(
            url,
            params={"recursive": "1"},
            headers=_build_headers(),
        )

    # Empty repositories (no commits) return 404 on the contents endpoint
    if response.status_code == 404:
        return []

    _handle_error_response(response)

    data = response.json()

    if data.get("truncated"):
        raise GitHubAPIError(f"Repository tree for '{repo}' is too large to analyze.")

    return [
        {
            "path": entry["path"],
            "name": entry["path"].split("/")[-1],
            "type": _TREE_TYPE_MAP.get(entry["type"], entry["type"]),
            "size": entry.get("size"),
        }
        for entry in data.get("tree", [])
    ]


async def get_file_content(owner: str, repo: str, path: str) -> str | None:
    """
    Fetch and decode the text content of a single file via the Contents API.

    Returns None (rather than raising) when the file is missing, or when its
    content cannot be interpreted as UTF-8 text (e.g. binary files, or files
    GitHub declines to inline for size reasons), callers that are gathering
    content for many files at once shouldn't have to special-case this.

    Raises:
        GitHubRateLimitError: if the rate limit has been exceeded (403).
        GitHubAPIError: for any other unexpected error response.
    """
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"

    async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT) as client:
        response = await client.get(url, headers=_build_headers())

    if response.status_code == 404:
        return None

    _handle_error_response(response)

    data = response.json()

    # Directories and submodules resolve to a list or a non-file "type";
    # only plain files with base64-encoded content are usable here.
    if not isinstance(data, dict) or data.get("type") != "file":
        return None
    if data.get("encoding") != "base64" or "content" not in data:
        return None

    try:
        raw_bytes = base64.b64decode(data["content"], validate=False)
        return raw_bytes.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None


async def get_repository_file_contents(
    owner: str,
    repo: str,
    entries: list[dict],
    filenames: frozenset[str] = CONTENT_TARGET_FILENAMES,
) -> dict[str, str]:
    """
    Download the content of every entry useful for content-based detection.

    Only files already known to exist (from `entries`, typically the output
    of get_repository_tree) and whose name is in `filenames` are requested;
    this never probes for files that may not exist, so it costs exactly one
    API request per useful file found, and zero otherwise. Downloads run
    concurrently. A failure fetching one file (rate limit, API error, or an
    undecodable file) is skipped rather than failing the whole batch.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        entries: Flat list of tree entries (path/name/type[/size]).
        filenames: Set of lowercase filenames to consider. Defaults to
            CONTENT_TARGET_FILENAMES.

    Returns:
        Dict mapping entry "path" to decoded text content, for every target
        file that was successfully fetched and decoded.
    """
    targets = select_content_targets(entries, filenames)
    if not targets:
        return {}

    results = await asyncio.gather(
        *(get_file_content(owner, repo, entry["path"]) for entry in targets),
        return_exceptions=True,
    )

    contents: dict[str, str] = {}
    for entry, result in zip(targets, results):
        if isinstance(result, (GitHubRateLimitError, GitHubAPIError)):
            continue
        if isinstance(result, BaseException):
            raise result
        if result is not None:
            contents[entry["path"]] = result
    return contents
