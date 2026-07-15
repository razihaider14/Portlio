import pytest

from app.aggregator.engine import (
    build_skill_profiles,
    detect_strengths,
    detect_weaknesses,
    generate_recommendations,
    score_repository_practice,
)
from app.aggregator.models import RepositorySkillData, SkillTier, TechnologyObservation
from app.detector.models import RuleCategory


def obs(name, category=RuleCategory.LANGUAGE, confidence=0.9):
    return TechnologyObservation(name=name, category=category, confidence=confidence)


def metadata(
    has_tests=False,
    has_ci_cd=False,
    maturity_tier="unknown",
    quality_tier="none",
    has_docker=False,
    has_kubernetes_manifests=False,
):
    return {
        "has_tests": has_tests,
        "has_ci_cd": has_ci_cd,
        "maturity": {"maturity_tier": maturity_tier},
        "documentation": {"quality_tier": quality_tier},
        "has_docker": has_docker,
        "has_kubernetes_manifests": has_kubernetes_manifests,
    }


class TestScoreRepositoryPractice:
    def test_no_evidence_scores_zero(self):
        practice = score_repository_practice(metadata())
        assert practice.score == 0
        assert practice.evidence == ()

    def test_empty_dict_scores_zero(self):
        practice = score_repository_practice({})
        assert practice.score == 0

    def test_has_tests_scores_one_point(self):
        practice = score_repository_practice(metadata(has_tests=True))
        assert practice.score == 1
        assert "test suite" in practice.evidence[0]

    def test_has_ci_cd_scores_one_point(self):
        practice = score_repository_practice(metadata(has_ci_cd=True))
        assert practice.score == 1

    def test_active_maturity_scores_one_point(self):
        practice = score_repository_practice(metadata(maturity_tier="active"))
        assert practice.score == 1

    def test_mature_maturity_scores_one_point(self):
        practice = score_repository_practice(metadata(maturity_tier="mature"))
        assert practice.score == 1

    def test_non_mature_tiers_score_zero(self):
        for tier in ("experimental", "stale", "archived", "fork", "unknown"):
            practice = score_repository_practice(metadata(maturity_tier=tier))
            assert practice.score == 0, f"tier {tier} unexpectedly scored"

    def test_good_documentation_scores_one_point(self):
        practice = score_repository_practice(metadata(quality_tier="good"))
        assert practice.score == 1

    def test_excellent_documentation_scores_one_point(self):
        practice = score_repository_practice(metadata(quality_tier="excellent"))
        assert practice.score == 1

    def test_weak_documentation_tiers_score_zero(self):
        for tier in ("none", "minimal", "fair"):
            practice = score_repository_practice(metadata(quality_tier=tier))
            assert practice.score == 0, f"tier {tier} unexpectedly scored"

    def test_docker_scores_one_point(self):
        practice = score_repository_practice(metadata(has_docker=True))
        assert practice.score == 1

    def test_kubernetes_scores_one_point(self):
        practice = score_repository_practice(metadata(has_kubernetes_manifests=True))
        assert practice.score == 1

    def test_docker_and_kubernetes_together_still_one_point(self):
        # containerization is a single evidence line, not two
        practice = score_repository_practice(
            metadata(has_docker=True, has_kubernetes_manifests=True)
        )
        assert practice.score == 1

    def test_all_signals_scores_max(self):
        practice = score_repository_practice(
            metadata(
                has_tests=True,
                has_ci_cd=True,
                maturity_tier="mature",
                quality_tier="excellent",
                has_docker=True,
            )
        )
        assert practice.score == 5
        assert practice.max_score == 5
        assert len(practice.evidence) == 5

    def test_missing_nested_keys_do_not_raise(self):
        practice = score_repository_practice({"has_tests": True})
        assert practice.score == 1


class TestBuildSkillProfiles:
    def test_empty_repositories_gives_empty_profiles(self):
        assert build_skill_profiles([]) == []

    def test_repository_with_no_technologies_contributes_nothing(self):
        repos = [RepositorySkillData(name="empty-repo", technologies=(), metadata={})]
        assert build_skill_profiles(repos) == []

    def test_single_repository_single_technology(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python", confidence=0.95),),
                metadata=metadata(has_tests=True, has_ci_cd=True),
            )
        ]
        profiles = build_skill_profiles(repos)
        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.name == "Python"
        assert profile.repository_count == 1
        assert profile.repositories == ("repo-a",)
        assert profile.average_detector_confidence == 0.95
        assert profile.average_practice_score == 2.0
        # breadth(1)=1 + confidence(0.95>=0.9)=2 + practice(2>=2)=1 => 4
        assert profile.score == 4
        assert profile.tier == SkillTier.PROFICIENT
        assert len(profile.evidence) == 3

    def test_same_technology_across_multiple_repos_aggregates(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python", confidence=0.9),),
                metadata=metadata(has_tests=True),
            ),
            RepositorySkillData(
                name="repo-b",
                technologies=(obs("Python", confidence=0.8),),
                metadata=metadata(has_ci_cd=True),
            ),
        ]
        profiles = build_skill_profiles(repos)
        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.repository_count == 2
        assert profile.repositories == ("repo-a", "repo-b")
        assert profile.average_detector_confidence == pytest.approx(0.85)
        assert profile.average_practice_score == 1.0

    def test_repositories_sorted_by_deduped_name(self):
        # same repo name appearing twice for the same tech should not
        # double count breadth
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python"), obs("Python")),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].repository_count == 1

    def test_multiple_distinct_technologies_produce_multiple_profiles(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Python", confidence=0.95),
                    obs("Django", category=RuleCategory.FRAMEWORK, confidence=0.9),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        names = {p.name for p in profiles}
        assert names == {"Python", "Django"}

    def test_sorted_by_score_descending_then_name(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Weak", confidence=0.5),
                    obs("Strong", confidence=0.95),
                ),
                metadata=metadata(
                    has_tests=True,
                    has_ci_cd=True,
                    maturity_tier="mature",
                    quality_tier="excellent",
                ),
            )
        ]
        profiles = build_skill_profiles(repos)
        assert [p.name for p in profiles] == ["Strong", "Weak"]

    def test_tie_break_by_name_ascending(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Zeta", confidence=0.9),
                    obs("Alpha", confidence=0.9),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        assert [p.name for p in profiles] == ["Alpha", "Zeta"]

    def test_majority_category_tie_broken_alphabetically(self):
        # same technology name observed with two different categories across
        # repos (shouldn't normally happen, but must resolve deterministically)
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("X", category=RuleCategory.TESTING),),
                metadata={},
            ),
            RepositorySkillData(
                name="repo-b",
                technologies=(obs("X", category=RuleCategory.FRAMEWORK),),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        # FRAMEWORK vs TESTING: alphabetically "framework" < "testing"
        assert profiles[0].category == RuleCategory.FRAMEWORK

    def test_max_breadth_score_at_four_repos(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(obs("Python", confidence=1.0),),
                metadata=metadata(
                    has_tests=True,
                    has_ci_cd=True,
                    maturity_tier="mature",
                    quality_tier="excellent",
                ),
            )
            for i in range(4)
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].score == 7
        assert profiles[0].tier == SkillTier.EXPERT

    def test_single_repo_low_confidence_no_practice_is_exposure(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Cobol", confidence=0.5),),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].score == 1
        assert profiles[0].tier == SkillTier.EXPOSURE


class TestDetectStrengthsAndWeaknesses:
    def _profile(self, name, score, tier):
        repos = None
        return name, score, tier

    def test_strengths_are_proficient_and_expert_only(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(obs("Strong", confidence=1.0),),
                metadata=metadata(
                    has_tests=True,
                    has_ci_cd=True,
                    maturity_tier="mature",
                    quality_tier="excellent",
                ),
            )
            for i in range(4)
        ] + [
            RepositorySkillData(
                name="repo-weak",
                technologies=(obs("Weak", confidence=0.5),),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        strengths = detect_strengths(profiles)
        assert [p.name for p in strengths] == ["Strong"]

    def test_weaknesses_are_exposure_only(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(obs("Strong", confidence=1.0),),
                metadata=metadata(
                    has_tests=True,
                    has_ci_cd=True,
                    maturity_tier="mature",
                    quality_tier="excellent",
                ),
            )
            for i in range(4)
        ] + [
            RepositorySkillData(
                name="repo-weak",
                technologies=(obs("Weak", confidence=0.5),),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(profiles)
        assert [p.name for p in weaknesses] == ["Weak"]

    def test_no_strengths_or_weaknesses_when_empty(self):
        assert detect_strengths([]) == []
        assert detect_weaknesses([]) == []

    def test_developing_tier_is_neither_strength_nor_weakness(self):
        # 2 repos -> breadth=2, confidence 0.5 -> 0, no practice evidence -> 0
        # total score = 2 -> DEVELOPING
        repos = [
            RepositorySkillData(
                name="a", technologies=(obs("Mid", confidence=0.5),), metadata={}
            ),
            RepositorySkillData(
                name="b", technologies=(obs("Mid", confidence=0.5),), metadata={}
            ),
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].tier == SkillTier.DEVELOPING
        assert detect_strengths(profiles) == []
        assert detect_weaknesses(profiles) == []


class TestGenerateRecommendations:
    def _established_profile_repos(self, name, category=RuleCategory.FRAMEWORK):
        # 4 repos, high confidence, full practice -> guaranteed EXPERT tier
        return [
            RepositorySkillData(
                name=f"{name}-repo-{i}",
                technologies=(obs(name, category=category, confidence=1.0),),
                metadata=metadata(
                    has_tests=True,
                    has_ci_cd=True,
                    maturity_tier="mature",
                    quality_tier="excellent",
                ),
            )
            for i in range(4)
        ]

    def test_recommends_missing_complement(self):
        repos = self._established_profile_repos("Django")
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        assert any(r.skill == "pytest" for r in recs)
        rec = next(r for r in recs if r.skill == "pytest")
        assert rec.based_on == ("Django",)
        assert "Django" in rec.reason or "testing" in rec.reason.lower()

    def test_no_recommendation_when_complement_present(self):
        repos = self._established_profile_repos("Django") + [
            RepositorySkillData(
                name="test-repo",
                technologies=(
                    obs("pytest", category=RuleCategory.TESTING, confidence=0.9),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        assert not any(r.skill == "pytest" for r in recs)

    def test_no_recommendation_for_non_established_trigger(self):
        # single low-confidence, no-practice detection -> EXPOSURE tier,
        # should not trigger a recommendation
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Django", category=RuleCategory.FRAMEWORK, confidence=0.5),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        assert recs == []

    def test_empty_profiles_gives_no_recommendations(self):
        assert generate_recommendations([]) == []

    def test_multiple_triggers_for_same_recommendation_merge(self):
        repos = self._established_profile_repos(
            "pytest", category=RuleCategory.TESTING
        ) + self._established_profile_repos("Jest", category=RuleCategory.TESTING)
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        gha = next(r for r in recs if r.skill == "GitHub Actions")
        assert set(gha.based_on) == {"pytest", "Jest"}

    def test_recommendations_sorted_by_trigger_strength_then_name(self):
        # Django (established) -> pytest; Python (established) -> Ruff
        repos = self._established_profile_repos(
            "Django", category=RuleCategory.FRAMEWORK
        ) + self._established_profile_repos("Python", category=RuleCategory.LANGUAGE)
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        rec_skills = [r.skill for r in recs]
        # both triggers tie at max score (7); tie-break is by skill name
        assert rec_skills == sorted(rec_skills)
