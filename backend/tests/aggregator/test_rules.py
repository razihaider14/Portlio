import pytest

from app.aggregator.models import SkillTier
from app.aggregator.rules import (
    COMPLEMENT_RULES,
    PRACTICE_MAX_SCORE,
    SKILL_MAX_SCORE,
    ComplementRule,
    breadth_points,
    confidence_points,
    practice_points,
    tier_for_score,
)
from app.detector.models import RuleCategory


class TestBreadthPoints:
    @pytest.mark.parametrize(
        "repository_count,expected",
        [
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 2),
            (4, 3),
            (10, 3),
        ],
    )
    def test_bucketing(self, repository_count, expected):
        assert breadth_points(repository_count) == expected


class TestConfidencePoints:
    @pytest.mark.parametrize(
        "confidence,expected",
        [
            (0.0, 0),
            (0.5, 0),
            (0.74, 0),
            (0.75, 1),
            (0.8, 1),
            (0.89, 1),
            (0.9, 2),
            (1.0, 2),
        ],
    )
    def test_bucketing(self, confidence, expected):
        assert confidence_points(confidence) == expected


class TestPracticePoints:
    @pytest.mark.parametrize(
        "practice_score,expected",
        [
            (0.0, 0),
            (1.99, 0),
            (2.0, 1),
            (3.0, 1),
            (3.99, 1),
            (4.0, 2),
            (5.0, 2),
        ],
    )
    def test_bucketing(self, practice_score, expected):
        assert practice_points(practice_score) == expected


class TestTierForScore:
    @pytest.mark.parametrize(
        "score,expected_tier",
        [
            (0, SkillTier.EXPOSURE),
            (1, SkillTier.EXPOSURE),
            (2, SkillTier.DEVELOPING),
            (3, SkillTier.DEVELOPING),
            (4, SkillTier.PROFICIENT),
            (5, SkillTier.PROFICIENT),
            (6, SkillTier.EXPERT),
            (7, SkillTier.EXPERT),
        ],
    )
    def test_thresholds(self, score, expected_tier):
        assert tier_for_score(score) == expected_tier

    def test_max_score_is_expert(self):
        assert tier_for_score(SKILL_MAX_SCORE) == SkillTier.EXPERT


class TestRubricMaxScores:
    def test_practice_max_score_matches_rubric_line_count(self):
        # 5 documented, independent evidence lines in score_repository_practice
        assert PRACTICE_MAX_SCORE == 5

    def test_skill_max_score_matches_subscore_sum(self):
        # breadth (3) + confidence (2) + practice (2)
        assert SKILL_MAX_SCORE == 3 + 2 + 2


class TestComplementRule:
    def test_valid_rule_construction(self):
        rule = ComplementRule(
            trigger="Django",
            complements=("pytest",),
            recommended="pytest",
            category=RuleCategory.TESTING,
            reason="because",
        )
        assert rule.recommended == "pytest"

    def test_recommended_not_in_complements_raises(self):
        with pytest.raises(ValueError):
            ComplementRule(
                trigger="Django",
                complements=("unittest",),
                recommended="pytest",
                category=RuleCategory.TESTING,
                reason="because",
            )


class TestComplementRulesRegistry:
    def test_registry_is_nonempty(self):
        assert len(COMPLEMENT_RULES) > 0

    def test_every_rule_recommended_is_in_its_own_complements(self):
        for rule in COMPLEMENT_RULES:
            assert rule.recommended in rule.complements

    def test_no_rule_recommends_its_own_trigger(self):
        for rule in COMPLEMENT_RULES:
            assert rule.recommended != rule.trigger

    def test_every_rule_has_a_nonempty_reason(self):
        for rule in COMPLEMENT_RULES:
            assert rule.reason.strip() != ""

    def test_triggers_are_unique(self):
        # one rule per trigger keeps recommendation generation unambiguous;
        # if this ever needs to change, generate_recommendations()'s
        # dedup-by-recommended-skill logic should be revisited too
        triggers = [rule.trigger for rule in COMPLEMENT_RULES]
        assert len(triggers) == len(set(triggers))
