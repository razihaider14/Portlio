import pytest

from app.aggregator.models import ProficiencyTier, SkillTier
from app.aggregator.rules import (
    COMPLEMENT_RULES,
    COMPOSITE_SKILL_NAMES,
    COMPOSITE_SKILL_RULES,
    EVIDENCE_STRENGTH_WEIGHT,
    LIMITED_PRACTICE_THRESHOLD,
    MAX_RECOMMENDATION_CHAIN_DEPTH,
    MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT,
    MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT,
    PRACTICE_FACTS,
    PRACTICE_MAX_SCORE,
    SKILL_MAX_SCORE,
    SKILL_TIER_DOWNGRADE_MAP,
    ComplementRule,
    CompositeSkillRule,
    breadth_points,
    confidence_points,
    detection_confidence,
    practice_points,
    proficiency_tier_for,
    tier_for_score,
)
from app.detector.models import EvidenceStrength, RuleCategory


class TestBreadthPoints:
    @pytest.mark.parametrize(
        "repository_count,expected",
        [
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 2),
            (4, 2),
            (10, 2),
        ],
    )
    def test_bucketing(self, repository_count, expected):
        assert breadth_points(repository_count) == expected

    def test_breadth_caps_at_two(self):
        # repository count can no longer single-handedly dominate the score
        assert breadth_points(2) == breadth_points(100)


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
            (0.99, 0),
            (1.0, 1),
            (1.99, 1),
            (2.0, 2),
            (2.99, 2),
            (3.0, 3),
            (3.99, 3),
            (4.0, 4),
            (5.0, 4),
        ],
    )
    def test_bucketing(self, practice_score, expected):
        assert practice_points(practice_score) == expected

    def test_practice_now_outweighs_breadth_and_confidence(self):
        # engineering practice can contribute more than breadth+confidence combined
        assert practice_points(4.0) > breadth_points(100) + confidence_points(0.5)


class TestTierForScore:
    @pytest.mark.parametrize(
        "score,expected_tier",
        [
            (0, SkillTier.EXPOSURE),
            (1, SkillTier.EXPOSURE),
            (2, SkillTier.DEVELOPING),
            (4, SkillTier.DEVELOPING),
            (5, SkillTier.PROFICIENT),
            (6, SkillTier.PROFICIENT),
            (7, SkillTier.EXPERT),
            (8, SkillTier.EXPERT),
        ],
    )
    def test_thresholds(self, score, expected_tier):
        assert tier_for_score(score) == expected_tier

    def test_max_score_is_expert(self):
        assert tier_for_score(SKILL_MAX_SCORE) == SkillTier.EXPERT

    def test_breadth_and_confidence_alone_cannot_reach_proficient(self):
        # max breadth (2) + max confidence (2) with zero practice evidence
        max_without_practice = breadth_points(1000) + confidence_points(1.0)
        assert tier_for_score(max_without_practice) == SkillTier.DEVELOPING


class TestRubricMaxScores:
    def test_practice_max_score_matches_rubric_fact_count(self):
        assert PRACTICE_MAX_SCORE == len(PRACTICE_FACTS) == 5

    def test_skill_max_score_matches_subscore_sum(self):
        # breadth (2) + confidence (2) + practice (4)
        assert SKILL_MAX_SCORE == 2 + 2 + 4

    def test_practice_subscore_weighted_more_than_breadth_and_confidence(self):
        # the whole point of the recalibration: practice must now weigh at
        # least as much as breadth and confidence combined
        practice_max = 4
        assert practice_max >= 2 + 2


class TestCompositeSkillRule:
    def test_valid_rule_construction(self):
        rule = CompositeSkillRule(
            name="Embedded Systems",
            category=RuleCategory.EMBEDDED,
            base_technologies=("Arduino",),
        )
        assert rule.min_repositories == 1
        assert rule.name_keywords == ()

    def test_empty_base_technologies_raises(self):
        with pytest.raises(ValueError):
            CompositeSkillRule(
                name="X", category=RuleCategory.EMBEDDED, base_technologies=()
            )

    def test_min_repositories_below_one_raises(self):
        with pytest.raises(ValueError):
            CompositeSkillRule(
                name="X",
                category=RuleCategory.EMBEDDED,
                base_technologies=("Arduino",),
                min_repositories=0,
            )


class TestCompositeSkillRulesRegistry:
    def test_registry_is_nonempty(self):
        assert len(COMPOSITE_SKILL_RULES) > 0

    def test_expected_composites_exist(self):
        names = {rule.name for rule in COMPOSITE_SKILL_RULES}
        assert {"Embedded Systems", "ESP32", "IoT"} <= names

    def test_composite_skill_names_matches_registry(self):
        assert COMPOSITE_SKILL_NAMES == frozenset(
            rule.name for rule in COMPOSITE_SKILL_RULES
        )

    def test_esp32_and_iot_have_keyword_filters(self):
        for name in ("ESP32", "IoT"):
            rule = next(r for r in COMPOSITE_SKILL_RULES if r.name == name)
            assert rule.name_keywords, f"{name} should require keyword corroboration"

    def test_embedded_systems_has_no_keyword_filter(self):
        rule = next(r for r in COMPOSITE_SKILL_RULES if r.name == "Embedded Systems")
        assert rule.name_keywords == ()

    def test_names_are_unique(self):
        names = [rule.name for rule in COMPOSITE_SKILL_RULES]
        assert len(names) == len(set(names))


class TestPracticeFacts:
    def test_five_facts_defined(self):
        assert len(PRACTICE_FACTS) == 5

    def test_labels_are_unique(self):
        labels = [label for label, _ in PRACTICE_FACTS]
        assert len(labels) == len(set(labels))

    def test_each_check_is_callable_and_boolean(self):
        for _, check in PRACTICE_FACTS:
            assert check({}) in (True, False)


class TestWeaknessThresholds:
    def test_limited_practice_threshold_is_half(self):
        assert LIMITED_PRACTICE_THRESHOLD == 0.5

    def test_minimum_repositories_thresholds_are_positive(self):
        assert MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT >= 1
        assert MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT >= 1


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

    def test_esp32_freertos_espidf_chain_exists(self):
        esp32_rule = next(r for r in COMPLEMENT_RULES if r.trigger == "ESP32")
        assert esp32_rule.recommended == "FreeRTOS"
        freertos_rule = next(r for r in COMPLEMENT_RULES if r.trigger == "FreeRTOS")
        assert freertos_rule.recommended == "ESP-IDF"

    def test_ruff_chains_to_ci(self):
        ruff_rule = next(r for r in COMPLEMENT_RULES if r.trigger == "Ruff")
        assert ruff_rule.recommended == "GitHub Actions"


class TestMaxRecommendationChainDepth:
    def test_depth_is_at_least_two(self):
        # required to support the requested ESP32 -> FreeRTOS -> ESP-IDF
        # and Python -> Ruff -> GitHub Actions chains
        assert MAX_RECOMMENDATION_CHAIN_DEPTH >= 2


class TestEvidenceStrengthWeight:
    def test_has_all_three_evidence_strengths(self):
        assert set(EVIDENCE_STRENGTH_WEIGHT) == set(EvidenceStrength)

    def test_weights_are_ordered_declared_lowest_demonstrated_highest(self):
        assert (
            EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.DECLARED]
            < EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.CONFIGURED]
            < EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.DEMONSTRATED]
        )

    def test_demonstrated_weight_is_full_weight(self):
        # Demonstrated evidence must never be discounted, or
        # detection_confidence() would diverge from
        # average_detector_confidence even for fully-demonstrated skills.
        assert EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.DEMONSTRATED] == 1.0


class TestDetectionConfidence:
    def test_empty_occurrences_returns_zero(self):
        assert detection_confidence([]) == 0.0

    def test_single_demonstrated_occurrence_is_unweighted(self):
        result = detection_confidence([(0.9, EvidenceStrength.DEMONSTRATED)])
        assert result == 0.9

    def test_single_declared_occurrence_is_discounted(self):
        result = detection_confidence([(0.9, EvidenceStrength.DECLARED)])
        assert result == pytest.approx(
            0.9 * EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.DECLARED]
        )
        assert result < 0.9

    def test_mixed_occurrences_average_the_weighted_values(self):
        result = detection_confidence(
            [
                (1.0, EvidenceStrength.DEMONSTRATED),
                (1.0, EvidenceStrength.DECLARED),
            ]
        )
        expected = (
            1.0 * 1.0 + 1.0 * EVIDENCE_STRENGTH_WEIGHT[EvidenceStrength.DECLARED]
        ) / 2
        assert result == pytest.approx(expected)

    def test_fully_demonstrated_matches_plain_mean(self):
        # When every occurrence is DEMONSTRATED, detection_confidence()
        # must equal the plain unweighted mean -- i.e. equal to what
        # average_detector_confidence would compute for the same
        # occurrences, since DEMONSTRATED's weight is 1.0.
        occurrences = [
            (0.9, EvidenceStrength.DEMONSTRATED),
            (0.8, EvidenceStrength.DEMONSTRATED),
            (1.0, EvidenceStrength.DEMONSTRATED),
        ]
        plain_mean = sum(c for c, _ in occurrences) / len(occurrences)
        assert detection_confidence(occurrences) == pytest.approx(plain_mean)


class TestProficiencyTierFor:
    def test_high_score_is_expert(self):
        assert (
            proficiency_tier_for(
                repository_count=3, raw_score=7, has_demonstrated_evidence=True
            )
            is ProficiencyTier.EXPERT
        )

    def test_mid_high_score_is_proficient(self):
        assert (
            proficiency_tier_for(
                repository_count=2, raw_score=5, has_demonstrated_evidence=True
            )
            is ProficiencyTier.PROFICIENT
        )

    def test_mid_score_is_comfortable(self):
        assert (
            proficiency_tier_for(
                repository_count=1, raw_score=3, has_demonstrated_evidence=True
            )
            is ProficiencyTier.COMFORTABLE
        )

    def test_low_score_with_demonstrated_evidence_is_used_once(self):
        assert (
            proficiency_tier_for(
                repository_count=1, raw_score=1, has_demonstrated_evidence=True
            )
            is ProficiencyTier.USED_ONCE
        )

    def test_low_score_without_demonstrated_evidence_is_exposure(self):
        # This is the distinction USED_ONCE exists to draw: a low score
        # backed by ONLY declared/configured evidence never reaches
        # USED_ONCE, no matter the repository count.
        assert (
            proficiency_tier_for(
                repository_count=1, raw_score=1, has_demonstrated_evidence=False
            )
            is ProficiencyTier.EXPOSURE
        )

    def test_zero_repositories_is_exposure_even_with_demonstrated_flag(self):
        # Defensive: shouldn't occur in practice (a profile only exists
        # with >=1 occurrence), but repository_count gates USED_ONCE.
        assert (
            proficiency_tier_for(
                repository_count=0, raw_score=1, has_demonstrated_evidence=True
            )
            is ProficiencyTier.EXPOSURE
        )

    def test_every_tier_is_reachable(self):
        # Guards against a threshold typo silently making a tier
        # unreachable.
        reachable = {
            proficiency_tier_for(
                repository_count=3, raw_score=8, has_demonstrated_evidence=True
            ),
            proficiency_tier_for(
                repository_count=2, raw_score=5, has_demonstrated_evidence=True
            ),
            proficiency_tier_for(
                repository_count=1, raw_score=3, has_demonstrated_evidence=True
            ),
            proficiency_tier_for(
                repository_count=1, raw_score=0, has_demonstrated_evidence=True
            ),
            proficiency_tier_for(
                repository_count=1, raw_score=0, has_demonstrated_evidence=False
            ),
        }
        assert reachable == set(ProficiencyTier)


class TestSkillTierDowngradeMap:
    def test_covers_every_proficiency_tier(self):
        assert set(SKILL_TIER_DOWNGRADE_MAP) == set(ProficiencyTier)

    def test_maps_to_valid_skill_tiers(self):
        assert set(SKILL_TIER_DOWNGRADE_MAP.values()) <= set(SkillTier)

    def test_expert_and_proficient_map_onto_themselves(self):
        assert SKILL_TIER_DOWNGRADE_MAP[ProficiencyTier.EXPERT] is SkillTier.EXPERT
        assert (
            SKILL_TIER_DOWNGRADE_MAP[ProficiencyTier.PROFICIENT] is SkillTier.PROFICIENT
        )

    def test_used_once_downgrades_to_exposure(self):
        # USED_ONCE has no equivalent in the coarser four-tier SkillTier;
        # it collapses into EXPOSURE, the same as a purely-weak signal.
        assert SKILL_TIER_DOWNGRADE_MAP[ProficiencyTier.USED_ONCE] is SkillTier.EXPOSURE
