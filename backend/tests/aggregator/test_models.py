import pytest

from app.aggregator.models import (
    PortfolioSkillReport,
    RepositoryPractice,
    RepositorySkillData,
    SkillProfile,
    SkillRecommendation,
    SkillTier,
    TechnologyObservation,
)
from app.detector.models import RuleCategory


class TestTechnologyObservation:
    def test_valid_construction(self):
        obs = TechnologyObservation(
            name="Django", category=RuleCategory.FRAMEWORK, confidence=0.95
        )
        assert obs.name == "Django"
        assert obs.category is RuleCategory.FRAMEWORK
        assert obs.confidence == 0.95

    @pytest.mark.parametrize("confidence", [0.0, 1.0, 0.5])
    def test_boundary_confidences_are_valid(self, confidence):
        obs = TechnologyObservation(
            name="X", category=RuleCategory.LANGUAGE, confidence=confidence
        )
        assert obs.confidence == confidence

    @pytest.mark.parametrize("confidence", [-0.01, 1.01, -5, 5])
    def test_out_of_range_confidence_raises(self, confidence):
        with pytest.raises(ValueError):
            TechnologyObservation(
                name="X", category=RuleCategory.LANGUAGE, confidence=confidence
            )

    def test_is_frozen(self):
        obs = TechnologyObservation(
            name="Django", category=RuleCategory.FRAMEWORK, confidence=0.9
        )
        with pytest.raises(Exception):
            obs.name = "Flask"


class TestRepositorySkillData:
    def test_defaults(self):
        repo = RepositorySkillData(name="my-repo")
        assert repo.technologies == ()
        assert repo.metadata == {}

    def test_independent_default_metadata_dicts(self):
        # each instance must get its own dict, not a shared mutable default
        repo_a = RepositorySkillData(name="a")
        repo_b = RepositorySkillData(name="b")
        repo_a.metadata["mutated"] = True
        assert "mutated" not in repo_b.metadata


class TestRepositoryPractice:
    def test_construction(self):
        practice = RepositoryPractice(score=3, max_score=5, evidence=("has tests",))
        assert practice.score == 3
        assert practice.max_score == 5
        assert practice.evidence == ("has tests",)


class TestSkillProfile:
    def test_construction(self):
        profile = SkillProfile(
            name="Python",
            category=RuleCategory.LANGUAGE,
            repository_count=2,
            repositories=("a", "b"),
            average_detector_confidence=0.9,
            average_practice_score=3.0,
            score=5,
            max_score=7,
            tier=SkillTier.PROFICIENT,
            evidence=("some evidence",),
        )
        assert profile.tier is SkillTier.PROFICIENT
        assert profile.repositories == ("a", "b")


class TestSkillRecommendation:
    def test_construction(self):
        rec = SkillRecommendation(
            skill="pytest",
            category=RuleCategory.TESTING,
            reason="because",
            based_on=("Django",),
        )
        assert rec.skill == "pytest"
        assert rec.based_on == ("Django",)


class TestPortfolioSkillReport:
    def test_construction(self):
        report = PortfolioSkillReport(
            repository_count=0,
            skills=(),
            strengths=(),
            weaknesses=(),
            recommendations=(),
        )
        assert report.repository_count == 0
        assert report.skills == ()


class TestSkillTier:
    def test_is_string_enum(self):
        assert SkillTier.EXPERT == "expert"
        assert SkillTier.PROFICIENT.value == "proficient"
        assert SkillTier.DEVELOPING.value == "developing"
        assert SkillTier.EXPOSURE.value == "exposure"
