from datetime import datetime, timedelta, timezone

import pytest

from app.aggregator.aggregator import (
    aggregate_user_skills,
    aggregate_user_skills_detailed,
)
from app.aggregator.models import PortfolioSkillReport, SkillTier, TechnologyObservation
from app.detector.detector import detect_technologies_detailed
from app.detector.models import EvidenceStrength, MatchResult, RuleCategory
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
                "technologies": [
                    {"name": "Django", "category": "framework", "confidence": 0.9}
                ],
                "metadata": {},
            }
        ]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["category"] == "framework"

    def test_accepts_match_result_objects(self):
        match = MatchResult(
            name="Django",
            category=RuleCategory.FRAMEWORK,
            confidence=0.9,
            evidence_strength=EvidenceStrength.DEMONSTRATED,
            priority=5,
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
            name="Django",
            category=RuleCategory.FRAMEWORK,
            confidence=0.9,
            evidence_strength=EvidenceStrength.DEMONSTRATED,
            priority=5,
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
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Python", category="language")],
            }
        ]
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
                "technologies": [
                    _match_dict("Python", category="language", confidence=0.95)
                ],
                "metadata": {"has_tests": True},
            }
        ]
        result = aggregate_user_skills(repos)
        skill = result["skills"][0]
        assert isinstance(skill["category"], str)
        assert isinstance(skill["tier"], str)
        assert isinstance(skill["repositories"], list)
        assert isinstance(skill["evidence"], list)
        assert isinstance(skill["is_composite"], bool)

    def test_weakness_entry_is_json_friendly(self):
        repos = [
            {"name": f"repo-{i}", "technologies": [], "metadata": {}} for i in range(3)
        ]
        result = aggregate_user_skills(repos)
        assert result["weaknesses"], "expected at least one limited-practice weakness"
        weakness = result["weaknesses"][0]
        assert isinstance(weakness["kind"], str)
        assert isinstance(weakness["name"], str)
        assert weakness["category"] is None or isinstance(weakness["category"], str)
        assert isinstance(weakness["description"], str)
        assert isinstance(weakness["evidence"], list)

    def test_recommendation_entry_is_json_friendly(self):
        repos = [
            {
                "name": f"repo-{i}",
                "technologies": [
                    _match_dict("Django", category="framework", confidence=1.0)
                ],
                "metadata": {
                    "has_tests": True,
                    "has_ci_cd": True,
                    "maturity": {"maturity_tier": "mature"},
                    "documentation": {"quality_tier": "excellent"},
                    "has_docker": True,
                },
            }
            for i in range(2)
        ]
        result = aggregate_user_skills(repos)
        assert any(r["skill"] == "pytest" for r in result["recommendations"])
        rec = next(r for r in result["recommendations"] if r["skill"] == "pytest")
        assert isinstance(rec["category"], str)
        assert isinstance(rec["based_on"], list)
        assert isinstance(rec["chain"], list)


class TestAggregateUserSkillsPhase6Fields:
    """
    Phase 6: detection_confidence/proficiency_tier are new, additive keys
    on every skill entry. These tests guard the two halves of the
    backward-compatibility contract: (1) the new keys are present and
    correctly typed, and (2) the pre-existing "tier" key's possible values
    are exactly the original four strings -- a tripwire independent of any
    other test, so an accidental SkillTier value change (as opposed to the
    intended additive ProficiencyTier) would be caught here even if every
    other test happened not to exercise the affected value.
    """

    _ORIGINAL_TIER_VALUES = {"expert", "proficient", "developing", "exposure"}

    def test_skill_entry_has_new_additive_keys(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [
                    _match_dict("Python", category="language", confidence=0.95)
                ],
                "metadata": {"has_tests": True},
            }
        ]
        result = aggregate_user_skills(repos)
        skill = result["skills"][0]
        assert "detection_confidence" in skill
        assert "proficiency_tier" in skill
        assert isinstance(skill["detection_confidence"], float)
        assert isinstance(skill["proficiency_tier"], str)
        assert skill["proficiency_tier"] in {
            "exposure",
            "used_once",
            "comfortable",
            "proficient",
            "expert",
        }

    def test_tier_values_are_exactly_the_original_four_strings(self):
        # Tripwire: fails if SkillTier is ever extended/renamed instead of
        # ProficiencyTier being added alongside it (see
        # app.aggregator.models.SkillTier's docstring for why that
        # distinction matters -- "tier" is part of the undocumented-by-
        # Pydantic, silently-breakable stable API).
        repos = [
            {
                "name": f"repo-{i}",
                "technologies": [
                    _match_dict("Python", category="language", confidence=conf)
                ],
                "metadata": meta,
            }
            for i, (conf, meta) in enumerate(
                [
                    (0.5, {}),  # exposure-ish
                    (0.95, {"has_tests": True, "has_ci_cd": True}),  # stronger
                ]
            )
        ]
        result = aggregate_user_skills(repos)
        observed_tiers = {skill["tier"] for skill in result["skills"]}
        assert observed_tiers <= self._ORIGINAL_TIER_VALUES

    def test_accepts_dict_input_without_evidence_strength_key(self):
        # The pre-Phase-6 input contract (a plain 3-key dict) must keep
        # working unmodified -- evidence_strength is optional, not
        # required, on the external input shape.
        repos = [
            {
                "name": "repo-a",
                "technologies": [_match_dict("Django")],  # no evidence_strength key
                "metadata": {},
            }
        ]
        result = aggregate_user_skills(repos)
        assert result["skills"][0]["name"] == "Django"
        # Falls back to TechnologyObservation's default (DEMONSTRATED), so
        # detection_confidence should equal average_detector_confidence
        # for this single, otherwise-unweighted occurrence.
        skill = result["skills"][0]
        assert skill["detection_confidence"] == skill["average_detector_confidence"]

    def test_accepts_dict_input_with_string_evidence_strength(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [
                    {
                        "name": "SomeLib",
                        "category": "framework",
                        "confidence": 0.9,
                        "evidence_strength": "declared",
                    }
                ],
                "metadata": {},
            }
        ]
        result = aggregate_user_skills(repos)
        skill = result["skills"][0]
        # A DECLARED-only occurrence must be discounted below its raw
        # detector confidence in detection_confidence, while
        # average_detector_confidence (legacy) stays the raw value.
        assert skill["average_detector_confidence"] == 0.9
        assert skill["detection_confidence"] < 0.9


class TestAggregateUserSkillsDetailed:
    def test_returns_portfolio_skill_report(self):
        report = aggregate_user_skills_detailed([])
        assert isinstance(report, PortfolioSkillReport)

    def test_matches_dict_form_content(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [
                    _match_dict("Python", category="language", confidence=0.95)
                ],
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
        raw_repo = {
            "name": "empty",
            "contents": [],
            "file_contents": {},
            "repo_metadata": {},
        }
        aggregator_repo = self._build_aggregator_repo(raw_repo)
        result = aggregate_user_skills([aggregator_repo])
        assert result["skills"] == []
        assert result["repository_count"] == 1


class TestDeterminism:
    def test_same_input_produces_identical_output(self):
        repos = [
            {
                "name": "repo-a",
                "technologies": [
                    _match_dict("Python", category="language", confidence=0.9)
                ],
                "metadata": {"has_tests": True},
            },
            {
                "name": "repo-b",
                "technologies": [
                    _match_dict("Python", category="language", confidence=0.8)
                ],
                "metadata": {},
            },
        ]
        result_1 = aggregate_user_skills(repos)
        result_2 = aggregate_user_skills(repos)
        assert result_1 == result_2

    def test_repository_order_does_not_affect_skill_aggregation(self):
        repo_a = {
            "name": "repo-a",
            "technologies": [
                _match_dict("Python", category="language", confidence=0.9)
            ],
            "metadata": {"has_tests": True},
        }
        repo_b = {
            "name": "repo-b",
            "technologies": [
                _match_dict("Python", category="language", confidence=0.8)
            ],
            "metadata": {},
        }
        result_forward = aggregate_user_skills([repo_a, repo_b])
        result_reversed = aggregate_user_skills([repo_b, repo_a])
        assert result_forward["skills"] == result_reversed["skills"]


def _obs(name, category, confidence):
    return TechnologyObservation(name=name, category=category, confidence=confidence)


def _meta(
    has_tests=False, has_ci_cd=False, maturity="unknown", doc="none", docker=False
):
    return {
        "has_tests": has_tests,
        "has_ci_cd": has_ci_cd,
        "maturity": {"maturity_tier": maturity},
        "documentation": {"quality_tier": doc},
        "has_docker": docker,
    }


def razihaider14_portfolio_repos() -> list[dict]:
    """
    A reconstruction of the real `razihaider14` GitHub portfolio (10
    repositories) used to report the recalibration issues this revision
    fixes: HTML reaching "expert" purely on repository breadth, ESP32
    work being invisible under the generic "Arduino" label, and
    "weaknesses" almost always being empty.

    Per-repository technology sets and each skill's average detector
    confidence are taken directly from the real aggregated output that
    was reported (each technology's detector confidence is a fixed
    constant per app.detector.rules.Rule, so it's identical in every
    repository it's detected in). Per-repository *practice* facts are
    reconstructed to reproduce the exact reported average_practice_score
    per skill (solving the small linear system implied by which
    repositories share which skills), then intentionally distributed so
    that Testing (2/10), CI/CD (3/10), and Documentation (3/10) all fall
    below the reporting threshold, realistic for a personal/student
    portfolio, and exactly what's needed to exercise the new
    LIMITED_PRACTICE weakness detection end to end.
    """
    return [
        {
            "name": "NexEntry",
            "technologies": [
                _obs("HTML", RuleCategory.FRONTEND, 0.95),
                _obs("Arduino", RuleCategory.EMBEDDED, 1.0),
                _obs("C++", RuleCategory.LANGUAGE, 0.95),
            ],
            "metadata": _meta(maturity="active", doc="good"),
        },
        {
            "name": "NexLedger",
            "technologies": [
                _obs("HTML", RuleCategory.FRONTEND, 0.95),
                _obs("Arduino", RuleCategory.EMBEDDED, 1.0),
                _obs("C++", RuleCategory.LANGUAGE, 0.95),
            ],
            "metadata": _meta(maturity="active", docker=True),
        },
        {
            "name": "Sentinel",
            "technologies": [
                _obs("HTML", RuleCategory.FRONTEND, 0.95),
                _obs("Arduino", RuleCategory.EMBEDDED, 1.0),
            ],
            "metadata": _meta(has_tests=True, maturity="active"),
        },
        {
            "name": "razihaider14.github.io",
            "technologies": [_obs("HTML", RuleCategory.FRONTEND, 0.95)],
            "metadata": _meta(doc="good", maturity="active"),
        },
        {
            "name": "Arduino-IoT-Projects",
            "technologies": [_obs("Arduino", RuleCategory.EMBEDDED, 1.0)],
            "metadata": _meta(has_ci_cd=True),
        },
        {
            "name": "ESP32-RPi-MQTT",
            "technologies": [_obs("Arduino", RuleCategory.EMBEDDED, 1.0)],
            "metadata": _meta(maturity="active"),
        },
        {
            "name": "ESP32-Tone-Console",
            "technologies": [
                _obs("Arduino", RuleCategory.EMBEDDED, 1.0),
                _obs("C++", RuleCategory.LANGUAGE, 0.95),
            ],
            "metadata": _meta(has_ci_cd=True),
        },
        {
            "name": "NexHub-v1",
            "technologies": [_obs("PCB Design (Gerber)", RuleCategory.EMBEDDED, 0.9)],
            "metadata": _meta(doc="good", maturity="active"),
        },
        {
            "name": "ESP32-Deployed",
            "technologies": [_obs("Python", RuleCategory.LANGUAGE, 0.95)],
            "metadata": _meta(has_ci_cd=True, maturity="active"),
        },
        {
            "name": "Portlio",
            "technologies": [
                _obs("Python", RuleCategory.LANGUAGE, 0.95),
                _obs("FastAPI", RuleCategory.FRAMEWORK, 0.95),
                _obs("pytest", RuleCategory.TESTING, 0.95),
            ],
            "metadata": _meta(has_tests=True),
        },
    ]


class TestRazihaider14PortfolioRegression:
    """
    Regression tests pinning down the exact behavior the recalibration
    was asked to fix, using the reconstructed real portfolio above.
    """

    def test_repository_count(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        assert result["repository_count"] == 10

    def test_html_no_longer_reaches_expert_on_breadth_alone(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        html = next(s for s in result["skills"] if s["name"] == "HTML")
        assert html["repository_count"] == 4
        assert html["tier"] != "expert"
        assert html["tier"] == "proficient"

    def test_esp32_skill_is_produced_distinct_from_arduino(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        names = {s["name"] for s in result["skills"]}
        assert "Arduino" in names
        assert "ESP32" in names

        esp32 = next(s for s in result["skills"] if s["name"] == "ESP32")
        assert esp32["is_composite"] is True
        assert set(esp32["repositories"]) == {"ESP32-RPi-MQTT", "ESP32-Tone-Console"}
        # the two general-purpose repos (NexEntry, NexLedger, Sentinel)
        # must NOT count as ESP32 evidence just because they use Arduino
        assert "NexEntry" not in esp32["repositories"]

    def test_embedded_systems_and_iot_composites_present(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        names = {s["name"] for s in result["skills"]}
        assert "Embedded Systems" in names
        assert "IoT" in names

        embedded = next(s for s in result["skills"] if s["name"] == "Embedded Systems")
        # union of Arduino's 6 repos + PCB's 1 repo
        assert embedded["repository_count"] == 7

        iot = next(s for s in result["skills"] if s["name"] == "IoT")
        assert set(iot["repositories"]) == {"Arduino-IoT-Projects", "ESP32-RPi-MQTT"}

    def test_domain_specific_skills_are_not_starved_relative_to_generic_ones(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        by_name = {s["name"]: s for s in result["skills"]}
        # ESP32 (2 repos, strong confidence+practice) scores competitively
        # with Arduino (6 repos) despite far less breadth, breadth alone
        # no longer decides the ranking
        assert by_name["ESP32"]["score"] >= by_name["Arduino"]["score"] - 1

    def test_weaknesses_are_no_longer_empty(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        assert result["weaknesses"] != []

    def test_limited_ci_cd_and_testing_weaknesses_detected(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        limited_practice_names = {
            w["name"] for w in result["weaknesses"] if w["kind"] == "limited_practice"
        }
        assert "CI/CD" in limited_practice_names
        assert "Testing" in limited_practice_names

    def test_limited_frontend_breadth_weakness_detected(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        breadth_weaknesses = {
            w["name"] for w in result["weaknesses"] if w["kind"] == "limited_breadth"
        }
        assert "Frontend Breadth" in breadth_weaknesses

    def test_recommendations_include_esp32_chain(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        recs = {r["skill"]: r for r in result["recommendations"]}
        assert "FreeRTOS" in recs
        assert recs["FreeRTOS"]["based_on"] == ["ESP32"]
        assert "ESP-IDF" in recs
        assert recs["ESP-IDF"]["chain"] == ["FreeRTOS"]

    def test_recommendations_include_python_static_analysis_chain(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        recs = {r["skill"]: r for r in result["recommendations"]}
        assert "Ruff" in recs
        assert "Python" in recs["Ruff"]["based_on"]

    def test_recommendations_are_no_longer_sparse(self):
        result = aggregate_user_skills(razihaider14_portfolio_repos())
        # previously: Ruff, GitHub Actions (2 total). Recalibration adds
        # the ESP32 -> FreeRTOS -> ESP-IDF chain on top.
        assert len(result["recommendations"]) >= 4

    def test_full_result_is_json_serializable(self):
        import json

        result = aggregate_user_skills(razihaider14_portfolio_repos())
        json.dumps(result)  # raises on anything non-JSON-safe
