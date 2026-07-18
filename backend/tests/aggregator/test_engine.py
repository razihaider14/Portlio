import pytest

from app.aggregator.engine import (
    build_skill_profiles,
    detect_strengths,
    detect_weaknesses,
    generate_recommendations,
    score_repository_practice,
)
from app.aggregator.models import (
    RepositorySkillData,
    SkillTier,
    TechnologyObservation,
    WeaknessKind,
)
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


def full_practice_metadata():
    return metadata(
        has_tests=True,
        has_ci_cd=True,
        maturity_tier="mature",
        quality_tier="excellent",
        has_docker=True,
    )


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
        assert "Testing" in practice.evidence[0]

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
        practice = score_repository_practice(full_practice_metadata())
        assert practice.score == 5
        assert practice.max_score == 5
        assert len(practice.evidence) == 5

    def test_missing_nested_keys_do_not_raise(self):
        practice = score_repository_practice({"has_tests": True})
        assert practice.score == 1


class TestBuildSkillProfilesBaseScoring:
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
        # breadth(1 repo)=1 + confidence(0.95>=0.9)=2 + practice(2>=2,<3)=2 => 5
        assert profile.score == 5
        assert profile.tier == SkillTier.PROFICIENT
        assert len(profile.evidence) == 3
        assert profile.is_composite is False

    def test_breadth_caps_at_two_repositories(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(obs("Python", confidence=1.0),),
                metadata={},
            )
            for i in range(6)
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].repository_count == 6
        assert "2 breadth points" in profiles[0].evidence[0]

    def test_breadth_alone_cannot_reach_proficient(self):
        # many repositories, but zero confidence/practice evidence
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(obs("Cobol", confidence=0.5),),
                metadata={},
            )
            for i in range(10)
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].tier in (SkillTier.EXPOSURE, SkillTier.DEVELOPING)

    def test_full_practice_and_confidence_single_repo_can_reach_expert(self):
        # quality over quantity: one excellently-engineered repository
        # should be able to reach the top tier
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python", confidence=1.0),),
                metadata=full_practice_metadata(),
            )
        ]
        profiles = build_skill_profiles(repos)
        assert profiles[0].score == 1 + 2 + 4  # breadth + confidence + practice
        assert profiles[0].tier == SkillTier.EXPERT

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

    def test_repeated_repo_name_does_not_double_count_breadth(self):
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
                metadata=full_practice_metadata(),
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
        assert profiles[0].category == RuleCategory.FRAMEWORK


class TestCompositeSkillDerivation:
    def test_embedded_systems_derived_from_arduino(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        names = {p.name for p in profiles}
        assert "Embedded Systems" in names
        embedded = next(p for p in profiles if p.name == "Embedded Systems")
        assert embedded.is_composite is True
        assert embedded.category == RuleCategory.EMBEDDED
        assert "derived by rolling up" in embedded.evidence[-1]

    def test_embedded_systems_unions_multiple_base_technologies(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
            RepositorySkillData(
                name="repo-b",
                technologies=(
                    obs(
                        "PCB Design (Gerber)",
                        category=RuleCategory.EMBEDDED,
                        confidence=0.9,
                    ),
                ),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        embedded = next(p for p in profiles if p.name == "Embedded Systems")
        assert embedded.repository_count == 2
        assert embedded.repositories == ("repo-a", "repo-b")

    def test_esp32_requires_keyword_match_in_repo_name(self):
        repos = [
            RepositorySkillData(
                name="ESP32-Weather-Station",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
            RepositorySkillData(
                name="generic-arduino-project",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        esp32 = next(p for p in profiles if p.name == "ESP32")
        assert esp32.repository_count == 1
        assert esp32.repositories == ("ESP32-Weather-Station",)
        assert esp32.is_composite is True

    def test_esp32_absent_when_no_repo_name_matches(self):
        repos = [
            RepositorySkillData(
                name="generic-arduino-project",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        names = {p.name for p in profiles}
        assert "ESP32" not in names
        # but the broader umbrella still fires: evidence still exists,
        # just not specific enough to claim the ESP32 target
        assert "Embedded Systems" in names

    def test_esp32_keyword_matching_is_case_and_separator_insensitive(self):
        repos = [
            RepositorySkillData(
                name="esp_32-sensor-hub",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        assert any(p.name == "ESP32" for p in profiles)

    def test_iot_requires_networking_keyword(self):
        repos = [
            RepositorySkillData(
                name="Home-MQTT-Bridge",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
            RepositorySkillData(
                name="ESP32-Tone-Console",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        iot = next(p for p in profiles if p.name == "IoT")
        assert iot.repository_count == 1
        assert iot.repositories == ("Home-MQTT-Bridge",)

    def test_no_embedded_base_technology_produces_no_composites(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python", confidence=0.9),),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        names = {p.name for p in profiles}
        assert "Embedded Systems" not in names
        assert "ESP32" not in names
        assert "IoT" not in names

    def test_composite_scored_with_same_rubric_as_base_skills(self):
        repos = [
            RepositorySkillData(
                name="ESP32-Project",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata=full_practice_metadata(),
            )
        ]
        profiles = build_skill_profiles(repos)
        esp32 = next(p for p in profiles if p.name == "ESP32")
        # 1 repo -> breadth 1, confidence 1.0 -> 2, practice 5 -> 4
        assert esp32.score == 1 + 2 + 4
        assert esp32.tier == SkillTier.EXPERT

    def test_base_skill_unaffected_by_composite_derivation(self):
        repos = [
            RepositorySkillData(
                name="ESP32-Project",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        arduino = next(p for p in profiles if p.name == "Arduino")
        assert arduino.is_composite is False
        assert arduino.repository_count == 1


class TestDetectStrengths:
    def test_strengths_are_proficient_and_expert_only(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Strong", confidence=1.0),),
                metadata=full_practice_metadata(),
            ),
            RepositorySkillData(
                name="repo-weak",
                technologies=(obs("Weak", confidence=0.5),),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        strengths = detect_strengths(profiles)
        assert [p.name for p in strengths] == ["Strong"]

    def test_no_strengths_when_empty(self):
        assert detect_strengths([]) == []

    def test_developing_tier_is_not_a_strength(self):
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


class TestDetectWeaknessesShallowSkill:
    def test_shallow_skill_weakness_for_exposure_tier(self):
        repos = [
            RepositorySkillData(
                name="repo-a", technologies=(obs("Cobol", confidence=0.5),), metadata={}
            )
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        shallow = [w for w in weaknesses if w.kind == WeaknessKind.SHALLOW_SKILL]
        assert any(w.name == "Cobol" for w in shallow)

    def test_no_shallow_skill_weakness_for_well_evidenced_skill(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(obs("Python", confidence=1.0),),
                metadata=full_practice_metadata(),
            )
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        shallow = [w for w in weaknesses if w.kind == WeaknessKind.SHALLOW_SKILL]
        assert shallow == []

    def test_empty_portfolio_has_no_weaknesses(self):
        assert detect_weaknesses([], []) == []


class TestDetectWeaknessesLimitedPractice:
    def _repos(self, count, **fact_overrides):
        return [
            RepositorySkillData(
                name=f"repo-{i}", technologies=(), metadata=metadata(**fact_overrides)
            )
            for i in range(count)
        ]

    def test_no_judgement_below_minimum_repository_count(self):
        # only 2 repositories: too small a sample to call anything "limited"
        repos = self._repos(2)
        weaknesses = detect_weaknesses(repos, [])
        assert [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_PRACTICE] == []

    def test_limited_ci_cd_fires_below_half(self):
        repos = self._repos(3)  # none have CI/CD: 0/3
        weaknesses = detect_weaknesses(repos, [])
        limited = [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_PRACTICE]
        assert any(w.name == "CI/CD" for w in limited)

    def test_no_limited_practice_weakness_when_majority_has_the_fact(self):
        repos = [
            RepositorySkillData(
                name="a", technologies=(), metadata=metadata(has_ci_cd=True)
            ),
            RepositorySkillData(
                name="b", technologies=(), metadata=metadata(has_ci_cd=True)
            ),
            RepositorySkillData(
                name="c", technologies=(), metadata=metadata(has_ci_cd=False)
            ),
        ]
        weaknesses = detect_weaknesses(repos, [])
        limited = [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_PRACTICE]
        assert not any(w.name == "CI/CD" for w in limited)

    def test_exactly_half_does_not_trigger(self):
        # threshold is strictly "< 0.5"; exactly 50% is not "limited"
        repos = [
            RepositorySkillData(
                name="a", technologies=(), metadata=metadata(has_tests=True)
            ),
            RepositorySkillData(
                name="b", technologies=(), metadata=metadata(has_tests=True)
            ),
            RepositorySkillData(
                name="c", technologies=(), metadata=metadata(has_tests=False)
            ),
            RepositorySkillData(
                name="d", technologies=(), metadata=metadata(has_tests=False)
            ),
        ]
        weaknesses = detect_weaknesses(repos, [])
        limited = [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_PRACTICE]
        assert not any(w.name == "Testing" for w in limited)

    def test_description_reports_fraction(self):
        repos = self._repos(4)  # 0/4 have tests
        weaknesses = detect_weaknesses(repos, [])
        testing_weakness = next(
            w
            for w in weaknesses
            if w.kind == WeaknessKind.LIMITED_PRACTICE and w.name == "Testing"
        )
        assert "0 of 4" in testing_weakness.description

    def test_all_five_facts_are_independently_checkable(self):
        repos = self._repos(3)  # nothing set: all 5 facts should be "limited"
        weaknesses = detect_weaknesses(repos, [])
        limited_names = {
            w.name for w in weaknesses if w.kind == WeaknessKind.LIMITED_PRACTICE
        }
        assert limited_names == {
            "Testing",
            "CI/CD",
            "Maturity",
            "Documentation",
            "Containerization",
        }


class TestDetectWeaknessesLimitedBreadth:
    def test_single_technology_in_category_with_enough_breadth_fires(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(
                    obs("HTML", category=RuleCategory.FRONTEND, confidence=0.9),
                ),
                metadata={},
            )
            for i in range(3)
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        breadth_weaknesses = [
            w for w in weaknesses if w.kind == WeaknessKind.LIMITED_BREADTH
        ]
        assert any(w.name == "Frontend Breadth" for w in breadth_weaknesses)

    def test_no_breadth_weakness_below_minimum_repositories(self):
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("HTML", category=RuleCategory.FRONTEND, confidence=0.9),
                ),
                metadata={},
            )
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        assert [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_BREADTH] == []

    def test_no_breadth_weakness_with_multiple_technologies_in_category(self):
        repos = [
            RepositorySkillData(
                name=f"repo-{i}",
                technologies=(
                    obs("HTML", category=RuleCategory.FRONTEND, confidence=0.9),
                    obs("React", category=RuleCategory.FRONTEND, confidence=0.9),
                ),
                metadata={},
            )
            for i in range(3)
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        assert [w for w in weaknesses if w.kind == WeaknessKind.LIMITED_BREADTH] == []

    def test_composite_skills_excluded_from_breadth_diversity_count(self):
        # Arduino + PCB Design (Gerber) = 2 distinct EMBEDDED technologies,
        # but the derived "Embedded Systems"/"ESP32"/"IoT" composites must
        # not be counted as if they added independent tooling diversity
        repos = [
            RepositorySkillData(
                name="repo-a",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
            RepositorySkillData(
                name="repo-b",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
            RepositorySkillData(
                name="repo-c",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata={},
            ),
        ]
        profiles = build_skill_profiles(repos)
        # only "Arduino" is a real, direct embedded technology here, but
        # composites (Embedded Systems) are also in `profiles`
        assert any(p.name == "Embedded Systems" for p in profiles)
        weaknesses = detect_weaknesses(repos, profiles)
        breadth_weaknesses = [
            w for w in weaknesses if w.kind == WeaknessKind.LIMITED_BREADTH
        ]
        assert any(w.name == "Embedded Breadth" for w in breadth_weaknesses)


class TestDetectWeaknessesOrdering:
    def test_shallow_skills_sorted_before_other_kinds(self):
        repos = [
            RepositorySkillData(
                name="repo-a", technologies=(obs("Cobol", confidence=0.5),), metadata={}
            ),
            RepositorySkillData(name="repo-b", technologies=(), metadata=metadata()),
            RepositorySkillData(name="repo-c", technologies=(), metadata=metadata()),
        ]
        profiles = build_skill_profiles(repos)
        weaknesses = detect_weaknesses(repos, profiles)
        kinds = [w.kind for w in weaknesses]
        if (
            WeaknessKind.SHALLOW_SKILL in kinds
            and WeaknessKind.LIMITED_PRACTICE in kinds
        ):
            assert kinds.index(WeaknessKind.SHALLOW_SKILL) < kinds.index(
                WeaknessKind.LIMITED_PRACTICE
            )


class TestGenerateRecommendationsDirect:
    def _established_profile_repos(self, name, category=RuleCategory.FRAMEWORK):
        return [
            RepositorySkillData(
                name=f"{name}-repo-{i}",
                technologies=(obs(name, category=category, confidence=1.0),),
                metadata=full_practice_metadata(),
            )
            for i in range(2)
        ]

    def test_recommends_missing_complement(self):
        repos = self._established_profile_repos("Django")
        profiles = build_skill_profiles(repos)
        recs = generate_recommendations(profiles)
        pytest_rec = next(r for r in recs if r.skill == "pytest")
        assert pytest_rec.based_on == ("Django",)
        assert pytest_rec.chain == ()

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
        assert generate_recommendations(profiles) == []

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


class TestGenerateRecommendationsChaining:
    def _established_profile_repos(self, name, category=RuleCategory.EMBEDDED):
        return [
            RepositorySkillData(
                name=f"{name}-repo-{i}",
                technologies=(obs(name, category=category, confidence=1.0),),
                metadata=full_practice_metadata(),
            )
            for i in range(2)
        ]

    def test_esp32_chains_to_freertos_and_espidf(self):
        repos = self._established_profile_repos("ESP32")
        profiles = build_skill_profiles(repos)
        recs = {r.skill: r for r in generate_recommendations(profiles)}

        assert "FreeRTOS" in recs
        assert recs["FreeRTOS"].based_on == ("ESP32",)
        assert recs["FreeRTOS"].chain == ()

        assert "ESP-IDF" in recs
        assert recs["ESP-IDF"].based_on == ("ESP32",)
        assert recs["ESP-IDF"].chain == ("FreeRTOS",)

    def test_python_chains_to_ruff_and_github_actions(self):
        repos = self._established_profile_repos(
            "Python", category=RuleCategory.LANGUAGE
        )
        profiles = build_skill_profiles(repos)
        recs = {r.skill: r for r in generate_recommendations(profiles)}

        assert "Ruff" in recs
        assert recs["Ruff"].chain == ()

        assert "GitHub Actions" in recs
        assert recs["GitHub Actions"].based_on == ("Python",)
        assert recs["GitHub Actions"].chain == ("Ruff",)

    def test_chain_does_not_continue_past_max_depth(self):
        # ESP32 (depth 1: FreeRTOS) -> FreeRTOS (depth 2: ESP-IDF) -> stop
        repos = self._established_profile_repos("ESP32")
        profiles = build_skill_profiles(repos)
        recs = {r.skill for r in generate_recommendations(profiles)}
        assert "FreeRTOS" in recs
        assert "ESP-IDF" in recs
        # confirms no rule exists to walk further than ESP-IDF, i.e. the
        # chain naturally terminates rather than the depth cap being the
        # only thing stopping it
        from app.aggregator.rules import COMPLEMENT_RULES

        assert not any(rule.trigger == "ESP-IDF" for rule in COMPLEMENT_RULES)

    def test_direct_recommendation_prefers_shortest_chain_when_both_reachable(self):
        # pytest -> GitHub Actions directly (chain=()) AND
        # Python -> Ruff -> GitHub Actions (chain=("Ruff",)); the shorter
        # path must win regardless of which established skill is processed
        # first
        repos = self._established_profile_repos(
            "Python", category=RuleCategory.LANGUAGE
        ) + self._established_profile_repos("pytest", category=RuleCategory.TESTING)
        profiles = build_skill_profiles(repos)
        recs = {r.skill: r for r in generate_recommendations(profiles)}
        assert recs["GitHub Actions"].chain == ()
        assert set(recs["GitHub Actions"].based_on) == {"Python", "pytest"}

    def test_established_composite_skill_can_be_a_recommendation_root(self):
        # ESP32 here is itself a *composite*, derived skill; chaining
        # must work identically whether the trigger was detected directly
        # or derived
        repos = [
            RepositorySkillData(
                name=f"ESP32-repo-{i}",
                technologies=(
                    obs("Arduino", category=RuleCategory.EMBEDDED, confidence=1.0),
                ),
                metadata=full_practice_metadata(),
            )
            for i in range(2)
        ]
        profiles = build_skill_profiles(repos)
        esp32 = next(p for p in profiles if p.name == "ESP32")
        assert esp32.is_composite is True
        assert esp32.tier != SkillTier.EXPOSURE

        recs = {r.skill for r in generate_recommendations(profiles)}
        assert "FreeRTOS" in recs
        assert "ESP-IDF" in recs
