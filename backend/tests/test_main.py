"""
API-level tests for GET /analyze/{username}, exercised through FastAPI's
TestClient rather than by calling analyze_user_repositories() directly.

These complement tests/analyzer/test_analyzer.py by confirming the guarantee
holds all the way through HTTP serialization, the actual bytes returned to
a client must never contain "file_contents" or raw manifest text, and the
response shape for include_content=false must be unchanged from before this
feature existed.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

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


class TestAnalyzeEndpointDefaultBehavior:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_default_response_shape_unchanged(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE

        response = client.get("/analyze/octocat")

        assert response.status_code == 200
        mock_content.assert_not_called()
        body = response.json()
        assert body["username"] == "octocat"
        assert body["repository_count"] == 1
        assert set(body["repositories"][0].keys()) == {
            "name",
            "language",
            "contents",
            "technologies",
            "metadata",
            "skills",
        }
        assert "file_contents" not in response.text


class TestAnalyzeEndpointWithContent:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_include_content_improves_detection(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        response = client.get("/analyze/octocat?include_content=true")

        assert response.status_code == 200
        assert "FastAPI" in response.json()["repositories"][0]["technologies"]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_response_never_contains_file_contents_key(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        response = client.get("/analyze/octocat?include_content=true")

        assert "file_contents" not in response.text

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_response_never_contains_raw_manifest_text(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\nuvicorn\n"}

        response = client.get("/analyze/octocat?include_content=true")

        # Only the derived "technologies" list should be present, not the
        # downloaded manifest text itself.
        assert "fastapi==0.100" not in response.text
        assert "uvicorn" not in response.text

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_response_shape_identical_to_default_except_technologies(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {
            "requirements.txt": "some-internal-package\n"
        }  # no extra detection

        with_content = client.get("/analyze/octocat?include_content=true").json()
        without_content = client.get("/analyze/octocat?include_content=false").json()

        assert with_content == without_content

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_multiple_repositories_none_leak_file_contents(
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

        response = client.get("/analyze/octocat?include_content=true")

        body = response.json()
        assert body["repository_count"] == 2
        for repository in body["repositories"]:
            assert "file_contents" not in repository
        assert "file_contents" not in response.text


class TestAnalyzeEndpointMetadata:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_metadata_field_present_in_response(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE

        response = client.get("/analyze/octocat")

        assert response.status_code == 200
        metadata = response.json()["repositories"][0]["metadata"]
        assert "project_types" in metadata
        assert "documentation" in metadata
        assert "license" in metadata
        assert "maturity" in metadata
        assert "size_metrics" in metadata

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_metadata_computed_without_include_content(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = [
            {"path": "Dockerfile", "name": "Dockerfile", "type": "file"},
        ]

        response = client.get("/analyze/octocat")

        mock_content.assert_not_called()
        assert response.json()["repositories"][0]["metadata"]["has_docker"] is True

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_metadata_richer_with_include_content(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "flask\npytest\n"}

        response = client.get("/analyze/octocat?include_content=true")

        metadata = response.json()["repositories"][0]["metadata"]
        assert "api_backend" in metadata["project_types"]
        assert metadata["has_tests"] is True

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_raw_repo_metadata_never_leaks_into_response(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [
            {
                "name": "myrepo",
                "language": "Python",
                "owner": {"login": "octocat"},
                "html_url": "https://github.com/octocat/myrepo",
                "clone_url": "https://github.com/octocat/myrepo.git",
                "stargazers_count": 777,
            }
        ]
        mock_tree.return_value = FAKE_TREE

        response = client.get("/analyze/octocat")

        assert "html_url" not in response.text
        assert "clone_url" not in response.text
        assert "repo_metadata" not in response.text
        assert (
            response.json()["repositories"][0]["metadata"]["maturity"]["stars"] == 777
        )

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_response_shape_still_stable_with_metadata(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE

        response = client.get("/analyze/octocat")

        repository = response.json()["repositories"][0]
        assert set(repository.keys()) == {
            "name",
            "language",
            "contents",
            "technologies",
            "metadata",
            "skills",
        }
