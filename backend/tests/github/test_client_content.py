"""
Unit tests for the content-fetching additions to the GitHub client:
get_file_content() and get_repository_file_contents().

HTTP is mocked with respx; no real network calls are made.
"""

import base64

import httpx
import pytest
import respx

from app.github.client import (
    BASE_URL,
    GitHubAPIError,
    GitHubRateLimitError,
    get_file_content,
    get_repository_file_contents,
)


def _contents_response(
    text: str, encoding: str = "base64", type_: str = "file"
) -> dict:
    return {
        "type": type_,
        "encoding": encoding,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
    }


class TestGetFileContent:
    @respx.mock
    async def test_returns_decoded_text_content(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(
                200, json=_contents_response("fastapi==0.100\n")
            )
        )
        content = await get_file_content("octocat", "repo", "requirements.txt")
        assert content == "fastapi==0.100\n"

    @respx.mock
    async def test_returns_none_for_missing_file(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/missing.txt").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        content = await get_file_content("octocat", "repo", "missing.txt")
        assert content is None

    @respx.mock
    async def test_returns_none_for_non_utf8_binary_content(self):
        payload = {
            "type": "file",
            "encoding": "base64",
            "content": base64.b64encode(b"\xff\xfe\x00\x01binary").decode("ascii"),
        }
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/image.png").mock(
            return_value=httpx.Response(200, json=payload)
        )
        content = await get_file_content("octocat", "repo", "image.png")
        assert content is None

    @respx.mock
    async def test_returns_none_when_encoding_is_not_base64(self):
        payload = {"type": "file", "encoding": "none", "content": ""}
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/weird.txt").mock(
            return_value=httpx.Response(200, json=payload)
        )
        content = await get_file_content("octocat", "repo", "weird.txt")
        assert content is None

    @respx.mock
    async def test_returns_none_when_path_resolves_to_a_directory(self):
        # The Contents API returns a JSON array (not an object) for directories.
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/src").mock(
            return_value=httpx.Response(200, json=[{"type": "file", "name": "main.py"}])
        )
        content = await get_file_content("octocat", "repo", "src")
        assert content is None

    @respx.mock
    async def test_raises_rate_limit_error_on_403_rate_limit(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(
                403, json={"message": "API rate limit exceeded for xxx"}
            )
        )
        with pytest.raises(GitHubRateLimitError):
            await get_file_content("octocat", "repo", "requirements.txt")

    @respx.mock
    async def test_raises_api_error_on_unexpected_status(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(500, json={"message": "Internal Server Error"})
        )
        with pytest.raises(GitHubAPIError):
            await get_file_content("octocat", "repo", "requirements.txt")


class TestGetRepositoryFileContents:
    @respx.mock
    async def test_fetches_only_selected_target_files(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(200, json=_contents_response("fastapi\n"))
        )
        entries = [
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
            {"path": "main.py", "name": "main.py", "type": "file"},
        ]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {"requirements.txt": "fastapi\n"}
        # Exactly one HTTP call: main.py is never a content target, so it's
        # never requested.
        assert respx.calls.call_count == 1

    @respx.mock
    async def test_returns_empty_dict_when_no_entries_are_targets(self):
        entries = [{"path": "main.py", "name": "main.py", "type": "file"}]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {}
        assert respx.calls.call_count == 0

    @respx.mock
    async def test_fetches_multiple_targets_concurrently(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(200, json=_contents_response("fastapi\n"))
        )
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/package.json").mock(
            return_value=httpx.Response(200, json=_contents_response('{"name": "x"}'))
        )
        entries = [
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
            {"path": "package.json", "name": "package.json", "type": "file"},
        ]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {
            "requirements.txt": "fastapi\n",
            "package.json": '{"name": "x"}',
        }

    @respx.mock
    async def test_skips_individual_failures_without_failing_the_batch(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(200, json=_contents_response("fastapi\n"))
        )
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/package.json").mock(
            return_value=httpx.Response(500, json={"message": "boom"})
        )
        entries = [
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
            {"path": "package.json", "name": "package.json", "type": "file"},
        ]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {"requirements.txt": "fastapi\n"}

    @respx.mock
    async def test_skips_files_that_404(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/requirements.txt").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )
        entries = [
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
        ]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {}

    @respx.mock
    async def test_honors_custom_filenames_argument(self):
        respx.get(f"{BASE_URL}/repos/octocat/repo/contents/notes.md").mock(
            return_value=httpx.Response(200, json=_contents_response("hello"))
        )
        entries = [{"path": "notes.md", "name": "notes.md", "type": "file"}]
        contents = await get_repository_file_contents(
            "octocat", "repo", entries, filenames=frozenset({"notes.md"})
        )
        assert contents == {"notes.md": "hello"}

    async def test_respects_size_limit_from_tree_entries(self):
        # No HTTP mock registered at all: if size filtering works, no
        # request is ever attempted, so an unmocked call would raise.
        entries = [
            {
                "path": "requirements.txt",
                "name": "requirements.txt",
                "type": "file",
                "size": 10_000_000,
            }
        ]
        contents = await get_repository_file_contents("octocat", "repo", entries)
        assert contents == {}
