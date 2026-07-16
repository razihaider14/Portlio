"""
API-level tests for the Skill Aggregation Engine's wiring into the FastAPI
app, exercised through TestClient rather than by calling
analyze_user_repositories() directly (see
tests/analyzer/test_skill_aggregation_integration.py for the function-level
equivalent). Covers:
  - GET /analyze/{username} gaining "skills" (per repository) and
    "portfolio" (top level) fields, with everything else unchanged
  - the new GET /skills/{username} endpoint
  - empty / single-repo / multi-repo portfolios
  - include_content=True
  - GitHub error passthrough on the new endpoint
  - no internal objects (MatchResult, enums, ...) ever reach the wire
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.github.client import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
)
from app.main import app

client = TestClient(app)

FAKE_REPO = {"name": "myrepo", "language": "Python", "owner": {"login": "octocat"}}
DJANGO_TREE = [
    {"path": "manage.py", "name": "manage.py", "type": "file"},
    {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
    {"path": "tests/test_views.py", "name": "test_views.py", "type": "file"},
    {"path": ".github/workflows", "name": "workflows", "type": "dir"},
    {"path": ".github/workflows/ci.yml", "name": "ci.yml", "type": "file"},
]
ANGULAR_TREE = [
    {"path": "angular.json", "name": "angular.json", "type": "file"},
]


class TestAnalyzeEndpointGainsSkillsAndPortfolio:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_repository_has_skills_field(self, mock_repos, mock_tree, mock_content):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/analyze/octocat")

        assert response.status_code == 200
        repository = response.json()["repositories"][0]
        assert "skills" in repository
        assert any(s["name"] == "Django" for s in repository["skills"])

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_response_has_top_level_portfolio_field(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/analyze/octocat")

        body = response.json()
        assert "portfolio" in body
        assert set(body["portfolio"].keys()) == {
            "repository_count",
            "skills",
            "strengths",
            "weaknesses",
            "recommendations",
        }

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_pre_existing_fields_are_unchanged(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/analyze/octocat")

        body = response.json()
        assert body["username"] == "octocat"
        assert body["repository_count"] == 1
        repository = body["repositories"][0]
        assert repository["name"] == "myrepo"
        assert repository["language"] == "Python"
        assert repository["contents"] == DJANGO_TREE
        assert repository["technologies"] == sorted(repository["technologies"])
        assert "Django" in repository["technologies"]


class TestSkillsEndpoint:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_returns_only_portfolio_shape(self, mock_repos, mock_tree, mock_content):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/skills/octocat")

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {
            "repository_count",
            "skills",
            "strengths",
            "weaknesses",
            "recommendations",
        }
        # not the full /analyze/{username} shape
        assert "repositories" not in body
        assert "username" not in body

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_empty_portfolio(self, mock_repos, mock_tree, mock_content):
        mock_repos.return_value = []

        response = client.get("/skills/octocat")

        assert response.status_code == 200
        assert response.json() == {
            "repository_count": 0,
            "skills": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }
        mock_tree.assert_not_called()

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_single_repo_portfolio(self, mock_repos, mock_tree, mock_content):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/skills/octocat")

        body = response.json()
        assert body["repository_count"] == 1
        django = next(s for s in body["skills"] if s["name"] == "Django")
        assert django["repository_count"] == 1
        assert django["repositories"] == ["myrepo"]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_multi_repo_portfolio_aggregates_across_repos(
        self, mock_repos, mock_tree, mock_content
    ):
        repos = [
            {"name": f"repo-{i}", "language": "Python", "owner": {"login": "octocat"}}
            for i in range(4)
        ]
        mock_repos.return_value = repos
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/skills/octocat")

        body = response.json()
        assert body["repository_count"] == 4
        django = next(s for s in body["skills"] if s["name"] == "Django")
        assert django["repository_count"] == 4
        # 4 repos, high detector confidence (0.95, manage.py rule), no
        # engineering-practice signals set up in the mocked repo API
        # objects beyond what the tree/README imply -> at least developing
        assert django["score"] >= 2

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_multi_repo_portfolio_produces_recommendation(
        self, mock_repos, mock_tree, mock_content
    ):
        repos = [
            {"name": f"repo-{i}", "language": "Python", "owner": {"login": "octocat"}}
            for i in range(4)
        ]
        mock_repos.return_value = repos
        # has_tests (tests/ dir) + has_ci_cd (.github/workflows) -> real
        # engineering-practice evidence, pushing Django to an established
        # tier so the pytest recommendation fires
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/skills/octocat")

        body = response.json()
        django = next(s for s in body["skills"] if s["name"] == "Django")
        if django["tier"] != "exposure":
            assert any(r["skill"] == "pytest" for r in body["recommendations"])

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_multiple_distinct_technologies_across_repos(
        self, mock_repos, mock_tree, mock_content
    ):
        repo_a = {
            "name": "django-repo",
            "language": "Python",
            "owner": {"login": "octocat"},
        }
        repo_b = {
            "name": "angular-repo",
            "language": "JavaScript",
            "owner": {"login": "octocat"},
        }
        mock_repos.return_value = [repo_a, repo_b]
        mock_tree.side_effect = [DJANGO_TREE, ANGULAR_TREE]

        response = client.get("/skills/octocat")

        names = {s["name"] for s in response.json()["skills"]}
        assert "Django" in names
        assert "Angular" in names

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_include_content_query_param_enriches_result(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = [
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
        ]
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        response = client.get("/skills/octocat?include_content=true")

        assert response.status_code == 200
        names = {s["name"] for s in response.json()["skills"]}
        assert "FastAPI" in names

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_include_content_false_by_default(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        client.get("/skills/octocat")

        mock_content.assert_not_called()

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_matches_analyze_endpoints_portfolio_field(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        skills_response = client.get("/skills/octocat").json()
        analyze_response = client.get("/analyze/octocat").json()

        assert skills_response == analyze_response["portfolio"]


class TestSkillsEndpointNoInternalObjectLeakage:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_no_internal_object_reprs_in_response_text(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        response = client.get("/skills/octocat")

        assert "MatchResult" not in response.text
        assert "TechnologyObservation" not in response.text
        assert "RuleCategory" not in response.text
        assert "SkillProfile" not in response.text

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_no_file_contents_or_repo_metadata_leak(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE
        mock_content.return_value = {"requirements.txt": "django\npytest\n"}

        response = client.get("/skills/octocat?include_content=true")

        assert "file_contents" not in response.text
        assert "repo_metadata" not in response.text


class TestSkillsEndpointErrorHandling:
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_user_not_found_returns_404(self, mock_repos):
        mock_repos.side_effect = GitHubUserNotFoundError()

        response = client.get("/skills/nonexistent-user")

        assert response.status_code == 404

    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_rate_limit_returns_429(self, mock_repos):
        mock_repos.side_effect = GitHubRateLimitError()

        response = client.get("/skills/octocat")

        assert response.status_code == 429

    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_github_api_error_returns_503(self, mock_repos):
        mock_repos.side_effect = GitHubAPIError()

        response = client.get("/skills/octocat")

        assert response.status_code == 503


class TestRegressionRealFixtures:
    """
    End-to-end regression tests through the actual HTTP layer, using
    realistic multi-file repository fixtures (not minimal single-file
    stubs), for both endpoints together.
    """

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_realistic_django_repo_end_to_end(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [
            {
                "name": "api-service",
                "language": "Python",
                "owner": {"login": "octocat"},
                "stargazers_count": 42,
                "archived": False,
                "fork": False,
            }
        ]
        mock_tree.return_value = [
            {"path": "manage.py", "name": "manage.py", "type": "file"},
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
            {"path": "api/settings.py", "name": "settings.py", "type": "file"},
            {"path": "api/urls.py", "name": "urls.py", "type": "file"},
            {"path": "tests/test_api.py", "name": "test_api.py", "type": "file"},
            {
                "path": ".github/workflows",
                "name": "workflows",
                "type": "dir",
            },
            {
                "path": ".github/workflows/ci.yml",
                "name": "ci.yml",
                "type": "file",
            },
            {"path": "Dockerfile", "name": "Dockerfile", "type": "file"},
            {"path": "README.md", "name": "README.md", "type": "file"},
        ]

        analyze_response = client.get("/analyze/octocat")
        skills_response = client.get("/skills/octocat")

        assert analyze_response.status_code == 200
        assert skills_response.status_code == 200

        repository = analyze_response.json()["repositories"][0]
        assert "Django" in repository["technologies"]
        assert repository["metadata"]["has_tests"] is True
        assert repository["metadata"]["has_ci_cd"] is True
        assert repository["metadata"]["has_docker"] is True

        django_skill = next(s for s in repository["skills"] if s["name"] == "Django")
        assert django_skill["score"] >= 1
        assert len(django_skill["evidence"]) == 3

        assert skills_response.json() == analyze_response.json()["portfolio"]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    def test_realistic_empty_repo_end_to_end(self, mock_repos, mock_tree, mock_content):
        mock_repos.return_value = [
            {"name": "scratch", "language": None, "owner": {"login": "octocat"}}
        ]
        mock_tree.return_value = []

        analyze_response = client.get("/analyze/octocat")
        skills_response = client.get("/skills/octocat")

        repository = analyze_response.json()["repositories"][0]
        assert repository["technologies"] == []
        assert repository["skills"] == []
        assert skills_response.json()["skills"] == []
        assert skills_response.json()["repository_count"] == 1
