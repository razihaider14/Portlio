from datetime import datetime, timedelta, timezone

import pytest

from app.aggregator.aggregator import (
    aggregate_user_skills,
    aggregate_user_skills_detailed,
)
from app.aggregator.models import PortfolioSkillReport, SkillTier, TechnologyObservation
from app.detector.detector import detect_technologies_detailed
from app.detector.models import MatchResult, RuleCategory
from app.metadata.metadata_analyzer import analyze_repository_metadata


def _match_dict(name, category="framework", confidence=0.9):
    return {"name": name, "category": category, "confidence": confidence}


class TestNormalizationOfTechnologyInputShapes:
    def test_accepts_plain_dicts(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Django")],
                "metadata": {},
            }
        ]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["name"] == "Django"

    def test_accepts_dict_with_string_category(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [{"name": "Django", "category": "framework", "confidence": 0.9}],
                "metadata": {},
            }
        ]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["category"] == "framework"

    def test_accepts_match_result_objects(self):
        match = MatchResult(
            name="Django", category=RuleCategory.FRAMEWORK, confidence=0.9, priority=5
        )
        repos = [{"name": "repo-a", "technologies": [match], "metadata": {}}]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["name"] == "Django"

    def test_accepts_technology_observation_objects(self):
        obs = TechnologyObservation(
            name="Django", category=RuleCategory.FRAMEWORK, confidence=0.9
        )
        repos = [{"name": "repo-a", "technologies": [obs], "metadata": {}}]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["name"] == "Django"

    def test_mixed_shapes_in_same_call(self):
        match = MatchResult(
            name="Django", category=RuleCategory.FRAMEWORK, confidence=0.9, priority=5
        )
        repos = [
            {"name": "repo-a", "technologies": [match], "metadata": {}},
            {
                "name": "repo-b",
                "technologies": [_match_dict("Django")],
                "metadata": {},
            },
        ]
        result = aggregate_user_skills(repos)
        assert len(result["skills"]) == 1
        assert result["skills"][0]["repository_count"] == 2


class TestAggregateUserSkillsShape:
    def test_top_level_keys(self):
        result = aggregate_user_skills([])
        assert set(result.keys()) == {
            "repository_count",
            "skills",
            "strengths",
            "weaknesses",
            "recommendations",
        }

    def test_empty_input(self):
        result = aggregate_user_skills([])
        assert result["repository_count"] == 0
        assert result["skills"] == []
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["recommendations"] == []

    def test_repository_with_missing_metadata_key(self):
        repos = [{"name": "repo-a", "technologies": [_match_dict("Python", category="language")]}]
        result = aggregate_user_skills(repos)
        assert result["repository_count"] == 1
        assert result["skills"][0]["name"] == "Python"

    def test_repository_with_missing_technologies_key(self):
        repos = [{"name": "repo-a", "metadata": {}}]
        result = aggregate_user_skills(repos)
        assert result["skills"] == []
        assert result["repository_count"] == 1

    def test_skill_entry_is_json_friendly(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Python", category="language", confidence=0.95)],
                "metadata": {"has_tests": True},
            }
        ]
        result = aggregate_user_skills(repos)
        skill = result["skills"][0]
        assert isinstance(skill["category"], str)
        assert isinstance(skill["tier"], str)
        assert isinstance(skill["repositories"], list)
        assert isinstance(skill["evidence"], list)

    def test_recommendation_entry_is_json_friendly(self):
        repos = [
            {
                "name": f"repo-{i}",
                "technologies": [_match_dict("Django", category="framework", confidence=1.0)],
                "metadata": {
                    "has_tests": True,
                    "has_ci_cd": True,
                    "maturity": {"maturity_tier": "mature"},
                    "documentation": {"quality_tier": "excellent"},
                },
            }
            for i in range(4)
        ]
        result = aggregate_user_skills(repos)
        assert any(r["skill"] == "pytest" for r in result["recommendations"])
        rec = next(r for r in result["recommendations"] if r["skill"] == "pytest")
        assert isinstance(rec["category"], str)
        assert isinstance(rec["based_on"], list)


class TestAggregateUserSkillsDetailed:
    def test_returns_portfolio_skill_report(self):
        report = aggregate_user_skills_detailed([])
        assert isinstance(report, PortfolioSkillReport)

    def test_matches_dict_form_content(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Python", category="language", confidence=0.95)],
                "metadata": {"has_tests": True},
            }
        ]
        detailed = aggregate_user_skills_detailed(repos)
        folded = aggregate_user_skills(repos)
        assert detailed.skills[0].name == folded["skills"][0]["name"]
        assert detailed.skills[0].score == folded["skills"][0]["score"]
        assert detailed.skills[0].tier.value == folded["skills"][0]["tier"]


class TestEndToEndIntegrationWithRealDetectorAndMetadata:
    """
    Regression tests that run this repository dict through the *real*
    detector and metadata analyzer (not hand-built fixtures), exactly as
    a real caller would, before feeding the results into the aggregator.
    """

    def _django_repo_with_practice(self, name="api-service"):
        contents = [
            {"path": "manage.py", "name": "manage.py", "type": "file"},
            {"path": "requirements.txt", "name": "requirements.txt", "type": "file"},
            {"path": "myapp/settings.py", "name": "settings.py", "type": "file"},
            {"path": "myapp/urls.py", "name": "urls.py", "type": "file"},
            {"path": "tests/test_views.py", "name": "test_views.py", "type": "file"},
            {"path": ".github/workflows/ci.yml", "name": "ci.yml", "type": "file"},
            {"path": "README.md", "name": "README.md", "type": "file"},
            {"path": "Dockerfile", "name": "Dockerfile", "type": "file"},
        ]
        file_contents = {
            "requirements.txt": "django>=4.2\ngunicorn\n",
            "README.md": "# API Service\n\n" + ("Documentation content. " * 50),
        }
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        recent_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        repo_metadata = {
            "archived": False,
            "fork": False,
            "created_at": old_timestamp,
            "pushed_at": recent_timestamp,
            "license": {"key": "mit"},
            "stargazers_count": 10,
        }
        return {
            "name": name,
            "contents": contents,
            "file_contents": file_contents,
            "repo_metadata": repo_metadata,
        }

    def _build_aggregator_repo(self, raw_repo):
        return {
            "name": raw_repo["name"],
            "technologies": detect_technologies_detailed(raw_repo),
            "metadata": analyze_repository_metadata(raw_repo),
        }

    def test_django_detected_and_aggregated(self):
        raw = self._django_repo_with_practice()
        aggregator_repo = self._build_aggregator_repo(raw)
        result = aggregate_user_skills([aggregator_repo])

        skill_names = {s["name"] for s in result["skills"]}
        assert "Django" in skill_names

    def test_pytest_recommendation_when_missing(self):
        raw = self._django_repo_with_practice()
        aggregator_repo = self._build_aggregator_repo(raw)
        # a single repo won't reach "established" tier on its own for every
        # rubric variant, so run it across four near-identical repos, the
        # same way a real multi-repo portfolio would look
        repos = [
            self._build_aggregator_repo(self._django_repo_with_practice(f"api-{i}"))
            for i in range(4)
        ]
        result = aggregate_user_skills(repos)
        django_skill = next(s for s in result["skills"] if s["name"] == "Django")
        assert django_skill["tier"] in ("proficient", "expert")
        assert any(r["skill"] == "pytest" for r in result["recommendations"])

    def test_evidence_strings_are_nonempty_for_detected_skill(self):
        raw = self._django_repo_with_practice()
        aggregator_repo = self._build_aggregator_repo(raw)
        result = aggregate_user_skills([aggregator_repo])
        django_skill = next(s for s in result["skills"] if s["name"] == "Django")
        assert len(django_skill["evidence"]) == 3
        assert all(isinstance(e, str) and e for e in django_skill["evidence"])

    def test_empty_repository_produces_no_skills(self):
        raw_repo = {"name": "empty", "contents": [], "file_contents": {}, "repo_metadata": {}}
        aggregator_repo = self._build_aggregator_repo(raw_repo)
        result = aggregate_user_skills([aggregator_repo])
        assert result["skills"] == []
        assert result["repository_count"] == 1


class TestDeterminism:
    def test_same_input_produces_identical_output(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Python", category="language", confidence=0.9)],
                "metadata": {"has_tests": True},
            },
            {
                "name": "repo-b",
                "technologies": [_match_dict("Python", category="language", confidence=0.8)],
                "metadata": {},
            },
        ]
        result_1 = aggregate_user_skills(repos)
        result_2 = aggregate_user_skills(repos)
        assert result_1 == result_2

    def test_repository_order_does_not_affect_skill_aggregation(self):
        repo_a = {
            "name": "repo-a",
            "technologies": [_match_dict("Python", category="language", confidence=0.9)],
            "metadata": {"has_tests": True},
        }
        repo_b = {
            "name": "repo-b",
            "technologies": [_match_dict("Python", category="language", confidence=0.8)],
            "metadata": {},
        }
        result_forward = aggregate_user_skills([repo_a, repo_b])
        result_reversed = aggregate_user_skills([repo_b, repo_a])
        assert result_forward["skills"] == result_reversed["skills"]
