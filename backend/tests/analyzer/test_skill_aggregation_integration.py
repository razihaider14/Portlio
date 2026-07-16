"""
Tests for the Skill Aggregation Engine wired into
app.analyzer.analyzer.analyze_user_repositories():
  - every repository gets its own "skills" field (that repository's
    technologies scored in isolation)
  - the top-level response gets a "portfolio" field (every repository's
    technologies + metadata aggregated together)
  - both fields are backward-compatible additions: all pre-existing fields
    are unchanged
  - no detector/aggregator internal objects (MatchResult,
    TechnologyObservation, ...) ever leak into the response

GitHub client calls are patched directly, mirroring
tests/analyzer/test_analyzer.py, so the real detector, metadata analyzer,
and aggregator run against realistic fixtures.
"""

import json
from unittest.mock import AsyncMock, patch

from app.aggregator.aggregator import aggregate_user_skills
from app.analyzer.analyzer import analyze_user_repositories
from app.detector.detector import detect_technologies_detailed
from app.metadata.metadata_analyzer import analyze_repository_metadata

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

DJANGO_TREE = [
    {"path": "manage.py", "name": "manage.py", "type": "file"},
    {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
    {"path": "myapp/settings.py", "name": "settings.py", "type": "file"},
    {"path": "tests/test_views.py", "name": "test_views.py", "type": "file"},
    {"path": ".github/workflows", "name": "workflows", "type": "dir"},
    {"path": ".github/workflows/ci.yml", "name": "ci.yml", "type": "file"},
]
ANGULAR_TREE = [
    {"path": "angular.json", "name": "angular.json", "type": "file"},
    {"path": "src/app/app.module.ts", "name": "app.module.ts", "type": "file"},
]


def _patchers():
    return (
        patch(
            "app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock
        ),
        patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock),
        patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock),
    )


class TestPerRepositorySkillsField:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_skills_field_present_on_every_repository(
        self, mock_repos, mock_tree, mock_content
    ):
        repo_a = {"name": "repo-a", "language": "Python", "owner": {"login": "octocat"}}
        repo_b = {"name": "repo-b", "language": "Go", "owner": {"login": "octocat"}}
        mock_repos.return_value = [repo_a, repo_b]
        mock_tree.return_value = FAKE_TREE

        result = await analyze_user_repositories("octocat")

        for repository in result["repositories"]:
            assert "skills" in repository
            assert isinstance(repository["skills"], list)

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_skills_scoped_to_its_own_repository(
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

        result = await analyze_user_repositories("octocat")

        django_repo = next(
            r for r in result["repositories"] if r["name"] == "django-repo"
        )
        angular_repo = next(
            r for r in result["repositories"] if r["name"] == "angular-repo"
        )

        django_skill_names = {s["name"] for s in django_repo["skills"]}
        angular_skill_names = {s["name"] for s in angular_repo["skills"]}

        assert "Django" in django_skill_names
        assert "Angular" not in django_skill_names
        assert "Angular" in angular_skill_names
        assert "Django" not in angular_skill_names

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_per_repository_skill_entries_report_repository_count_one(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        result = await analyze_user_repositories("octocat")

        repository = result["repositories"][0]
        for skill in repository["skills"]:
            # scored in isolation: this repository is the only evidence
            assert skill["repository_count"] == 1
            assert skill["repositories"] == [repository["name"]]

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_repository_with_no_technologies_has_empty_skills(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = []

        result = await analyze_user_repositories("octocat")

        assert result["repositories"][0]["technologies"] == []
        assert result["repositories"][0]["skills"] == []


class TestPortfolioField:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_portfolio_field_present_and_shaped(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        result = await analyze_user_repositories("octocat")

        assert "portfolio" in result
        assert set(result["portfolio"].keys()) == {
            "repository_count",
            "skills",
            "strengths",
            "weaknesses",
            "recommendations",
        }

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_empty_portfolio_for_user_with_no_repositories(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = []

        result = await analyze_user_repositories("octocat")

        assert result["repository_count"] == 0
        assert result["repositories"] == []
        assert result["portfolio"] == {
            "repository_count": 0,
            "skills": [],
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_single_repo_portfolio_matches_that_repositorys_skills(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        result = await analyze_user_repositories("octocat")

        # with exactly one repository, the portfolio is just that
        # repository's own skill view
        assert result["portfolio"]["skills"] == result["repositories"][0]["skills"]
        assert result["portfolio"]["repository_count"] == 1

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_multi_repo_portfolio_aggregates_breadth_across_repositories(
        self, mock_repos, mock_tree, mock_content
    ):
        repo_a = {"name": "repo-a", "language": "Python", "owner": {"login": "octocat"}}
        repo_b = {"name": "repo-b", "language": "Python", "owner": {"login": "octocat"}}
        repo_c = {"name": "repo-c", "language": "Python", "owner": {"login": "octocat"}}
        repo_d = {"name": "repo-d", "language": "Python", "owner": {"login": "octocat"}}
        mock_repos.return_value = [repo_a, repo_b, repo_c, repo_d]
        mock_tree.return_value = DJANGO_TREE  # every repo uses Django

        result = await analyze_user_repositories("octocat")

        # every individual repository sees Django in isolation (breadth=1)
        for repository in result["repositories"]:
            django_skill = next(
                s for s in repository["skills"] if s["name"] == "Django"
            )
            assert django_skill["repository_count"] == 1

        # but the portfolio sees it across all 4 repositories
        portfolio_django = next(
            s for s in result["portfolio"]["skills"] if s["name"] == "Django"
        )
        assert portfolio_django["repository_count"] == 4
        assert set(portfolio_django["repositories"]) == {
            "repo-a",
            "repo-b",
            "repo-c",
            "repo-d",
        }

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_multi_repo_portfolio_combines_distinct_technologies(
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

        result = await analyze_user_repositories("octocat")

        portfolio_names = {s["name"] for s in result["portfolio"]["skills"]}
        assert "Django" in portfolio_names
        assert "Angular" in portfolio_names


class TestIncludeContentEnrichesSkills:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_include_content_true_adds_content_detected_skill(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "fastapi==0.100\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        repository = result["repositories"][0]
        assert "FastAPI" in repository["technologies"]
        assert "FastAPI" in {s["name"] for s in repository["skills"]}
        assert "FastAPI" in {s["name"] for s in result["portfolio"]["skills"]}

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_include_content_false_by_default_does_not_fetch(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        await analyze_user_repositories("octocat")

        mock_content.assert_not_called()

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_include_content_does_not_change_shape_when_no_new_detection(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "some-internal-package\n"}

        with_content = await analyze_user_repositories("octocat", include_content=True)
        without_content = await analyze_user_repositories(
            "octocat", include_content=False
        )

        assert with_content == without_content


class TestNoInternalObjectLeakage:
    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_response_is_json_serializable(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = DJANGO_TREE

        result = await analyze_user_repositories("octocat")

        # raises if anything non-JSON-safe (e.g. a MatchResult/enum object)
        # leaked into the response
        serialized = json.dumps(result)
        assert "MatchResult" not in serialized
        assert "TechnologyObservation" not in serialized
        assert "RuleCategory" not in serialized

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_file_contents_and_repo_metadata_still_never_leak(
        self, mock_repos, mock_tree, mock_content
    ):
        mock_repos.return_value = [FAKE_REPO]
        mock_tree.return_value = FAKE_TREE
        mock_content.return_value = {"requirements.txt": "django\npytest\n"}

        result = await analyze_user_repositories("octocat", include_content=True)

        serialized = json.dumps(result)
        assert "file_contents" not in serialized
        assert "repo_metadata" not in serialized


class TestRegressionAgainstDirectAggregatorCall:
    """
    Confirms the pipeline's "portfolio" field is exactly what calling
    app.aggregator.aggregator.aggregate_user_skills() directly, on the same
    detector/metadata output, would produce, tying analyzer wiring to the
    aggregator's own documented contract rather than a re-implementation.
    """

    @patch("app.analyzer.analyzer.get_repository_file_contents", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_repository_tree", new_callable=AsyncMock)
    @patch("app.analyzer.analyzer.get_user_repositories", new_callable=AsyncMock)
    async def test_portfolio_matches_independent_aggregator_call(
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

        result = await analyze_user_repositories("octocat")

        # Rebuild the expected aggregator input independently, using the
        # same raw fixtures, and call the public aggregator API directly.
        expected_inputs = []
        for raw_repo, tree in ((repo_a, DJANGO_TREE), (repo_b, ANGULAR_TREE)):
            analysis_input = {"contents": tree, "repo_metadata": raw_repo}
            expected_inputs.append(
                {
                    "name": raw_repo["name"],
                    "technologies": detect_technologies_detailed(analysis_input),
                    "metadata": analyze_repository_metadata(analysis_input),
                }
            )
        expected_portfolio = aggregate_user_skills(expected_inputs)

        assert result["portfolio"] == expected_portfolio
