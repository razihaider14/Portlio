"""
Tests for app.analyzer.analyzer.analyze_user_repositories, focused on:
  - include_content is opt-in (no behavior change by default)
  - when enabled, downloaded content improves technology detection
  - downloaded content is an internal detail only: it must NEVER appear
    anywhere in the returned repository objects, whether or not
    include_content was used, and whether or not any content was found

GitHub client calls are patched directly rather than mocked over HTTP, since
the analyzer's contract with the client is what's under test here (the
client's own HTTP behavior is covered in tests/github/).
"""

import json
from unittest.mock import AsyncMock, patch

from app.analyzer.analyzer import analyze_user_repositories

FAKE_REPO = {"name": "myrepo", "language": "Python", "owner": {"login": "octocat"}}
FAKE_TREE = [
    {
        "path": "requirements.txt",
        "name": "requirements.txt",
        "type": "file",
        "size": 20,
    },
    {"path": "main.py", "name": "main.py", "type": "file", "size": 100},
]


class TestAnalyzeUserRepositoriesContentOptIn:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_does_not_fetch_content_by_default(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE

        result = await analyze_user_repositories("octocat")

        mock_content.assert_not_called()
        assert set(result["repositories"][0].keys()) == {
            "name",
            "language",
            "contents",
            "technologies",
            "metadata",
        }

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_fetches_content_when_opted_in(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        mock_content.assert_called_once_with("octocat", "myrepo", FAKE_TREE)
        # Content was fetched and used, but must not appear in the response.
        assert "file_contents" not in result["repositories"][0]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_content_flows_into_technology_detection(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        assert "FastAPI" in result["repositories"][0]["technologies"]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_response_shape_identical_with_or_without_content(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {
            "requirements.txt": "some-internal-package\n"
        }  # no rule hit

        with_content = await analyze_user_repositories("octocat", include_content=True)
        without_content = await analyze_user_repositories(
            "octocat", include_content=False
        )

        # Same shape, same technologies (since the content didn't add any
        # extra detection in this case), include_content must not alter
        # the response structure at all, only (optionally) the
        # "technologies" contents.
        assert with_content == without_content

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_omits_file_contents_key_when_nothing_downloaded(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {}

        result = await analyze_user_repositories("octocat", include_content=True)

        assert "file_contents" not in result["repositories"][0]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_no_repositories_skips_content_fetch(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = []

        result = await analyze_user_repositories("octocat", include_content=True)

        mock_tree.assert_not_called()
        mock_content.assert_not_called()
        assert result["repositories"] == []


class TestFileContentsNeverLeaksToResponse:
    """
    file_contents is purely an internal detection detail. These tests
    assert its absence exhaustively: not just as a top-level key, but
    anywhere in the serialized response, across multiple repositories and
    regardless of whether content was actually found.
    """

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_no_file_contents_key_in_any_repository(
        self, mock_repos, mock_tree, mock_content
    ):
        repo_a = {"name": "repo-a", "language": "Python", "owner": {"login": "octocat"}}
        repo_b = {
            "name": "repo-b",
            "language": "JavaScript",
            "owner": {"login": "octocat"},
        }
        mock_repos.return_value = [repo_a, repo_b]
        mock_tree.return_value = FAKE_TREE
        mock_content.side_effect = [
            {"requirements.txt": "fastapi\n"},
            {"package.json": '{"dependencies": {"react": "^18.0.0"}}'},
        ]

        result = await analyze_user_repositories("octocat", include_content=True)

        for repository in result["repositories"]:
            assert "file_contents" not in repository

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_no_file_contents_substring_anywhere_in_json_response(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        serialized = json.dumps(result)
        assert "file_contents" not in serialized
        # The raw downloaded manifest text must not leak into the response
        # either, only the derived "technologies" list should reflect it.
        assert "fastapi==0.100" not in serialized

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_repository_dict_keys_are_exactly_the_stable_public_shape(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        assert set(result["repositories"][0].keys()) == {
            "name",
            "language",
            "contents",
            "technologies",
            "metadata",
        }


class TestMetadataPipelineIntegration:
    """
    Confirms app.metadata is properly wired into analyze_user_repositories():
    metadata is computed for every repository, runs even without
    include_content, gets richer with it, and raw repo_metadata/file_contents
    never leak into the response, mirroring the file_contents leak
    guarantees already established for technology detection.
    """

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_metadata_computed_without_include_content(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [
            {
                "name": "myrepo",
                "language": "Python",
                "owner": {"login": "octocat"},
                "stargazers_count": 10,
                "archived": False,
            }
        ]
        mock_tree.return_value = [
            {"path": "Dockerfile", "name": "Dockerfile", "type": "file"},
            {"path": "Makefile", "name": "Makefile", "type": "file"},
        ]

        result = await analyze_user_repositories("octocat")

        mock_content.assert_not_called()
        metadata = result["repositories"][0]["metadata"]
        assert metadata["has_docker"] is True
        assert "Make" in metadata["build_systems"]
        assert metadata["maturity"]["stars"] == 10

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_metadata_gets_richer_with_include_content(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "flask\npytest\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        metadata = result["repositories"][0]["metadata"]
        assert "api_backend" in metadata["project_types"]
        assert metadata["has_tests"] is True

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_repo_metadata_never_leaks_into_response(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [
            {
                "name": "myrepo",
                "language": "Python",
                "owner": {"login": "octocat"},
                "stargazers_count": 999,
                "html_url": "https://github.com/octocat/myrepo",
                "private": False,
            }
        ]
        mock_tree.return_value = FAKE_TREE

        result = await analyze_user_repositories("octocat")

        serialized = json.dumps(result)
        assert "repo_metadata" not in serialized
        assert "html_url" not in serialized
        # The raw count is exposed only via the derived "maturity" field,
        # not as a top-level leak of the whole GitHub repo object.
        assert result["repositories"][0]["metadata"]["maturity"]["stars"] == 999

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_metadata_present_for_every_repository(
        self, mock_repos, mock_tree, mock_content
    ):
        repo_a = {"name": "repo-a", "language": "Python", "owner": {"login": "octocat"}}
        repo_b = {"name": "repo-b", "language": "Go", "owner": {"login": "octocat"}}
        mock_repos.return_value = [repo_a, repo_b]
        mock_tree.return_value = FAKE_TREE

        result = await analyze_user_repositories("octocat")

        for repository in result["repositories"]:
            assert "metadata" in repository
            assert "size_metrics" in repository["metadata"]
