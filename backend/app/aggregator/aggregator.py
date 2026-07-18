"""
Public API for the skill aggregation engine.

Mirrors app.detector.detector / app.metadata.metadata_analyzer: a stable
two-tier public API on top of a pure internal engine. External callers use
aggregate_user_skills() for the stable, JSON-friendly dict form, or
aggregate_user_skills_detailed() for the richer PortfolioSkillReport form
with full evidence and typed enums.

Internal modules (engine, models, rules) are implementation details and
should not be imported directly by code outside app/aggregator/.

Input contract: this subsystem consumes the outputs of the technology
detector and the metadata analyzer, one entry per repository:

    {
        "name": "my-api",
        "technologies": [...],   # see _normalize_technology() below
        "metadata": {...},       # analyze_repository_metadata()'s return value
    }

Each "technologies" entry may be any of:
    - an app.detector.models.MatchResult (the direct return type of
      detect_technologies_detailed()),
    - an app.aggregator.models.TechnologyObservation,
    - or a plain dict with "name", "category", and "confidence" keys
      (e.g. a MatchResult round-tripped through JSON, with "category" as
      either the RuleCategory enum or its string value).

"metadata" is expected to be analyze_repository_metadata()'s return value,
but any dict (including {}) is accepted; missing keys simply contribute no
evidence rather than raising.

Response shape: see aggregate_user_skills()'s docstring below for the
authoritative, field-by-field definition of every key this subsystem ever
returns, including derived/composite skills, the three kinds of
portfolio weakness, and chained recommendations.
"""

from app.aggregator.engine import (
    build_skill_profiles,
    detect_strengths,
    detect_weaknesses,
    generate_recommendations,
)
from app.aggregator.models import (
    PortfolioSkillReport,
    PortfolioWeakness,
    RepositorySkillData,
    SkillProfile,
    SkillRecommendation,
    TechnologyObservation,
)
from app.detector.models import RuleCategory


def _normalize_technology(technology) -> TechnologyObservation:
    """Convert any accepted technology shape (see module docstring) to a TechnologyObservation."""
    if isinstance(technology, TechnologyObservation):
        return technology

    name = getattr(technology, "name", None)
    category = getattr(technology, "category", None)
    confidence = getattr(technology, "confidence", None)
    if (
        name is None
    ):  # not an attribute-based object (e.g. MatchResult); try dict access
        name = technology["name"]
        category = technology["category"]
        confidence = technology["confidence"]

    if isinstance(category, str):
        category = RuleCategory(category)

    return TechnologyObservation(
        name=name, category=category, confidence=float(confidence)
    )


def _to_repository_skill_data(repositories: list[dict]) -> list[RepositorySkillData]:
    """Convert the raw per-repository input dicts to typed RepositorySkillData."""
    return [
        RepositorySkillData(
            name=repository.get("name", ""),
            technologies=tuple(
                _normalize_technology(tech)
                for tech in repository.get("technologies") or []
            ),
            metadata=repository.get("metadata") or {},
        )
        for repository in repositories
    ]


def _serialize_skill(profile: SkillProfile) -> dict:
    return {
        "name": profile.name,
        "category": profile.category.value,
        "repository_count": profile.repository_count,
        "repositories": list(profile.repositories),
        "average_detector_confidence": round(profile.average_detector_confidence, 4),
        "average_practice_score": round(profile.average_practice_score, 4),
        "score": profile.score,
        "max_score": profile.max_score,
        "tier": profile.tier.value,
        "evidence": list(profile.evidence),
        "is_composite": profile.is_composite,
    }


def _serialize_weakness(weakness: PortfolioWeakness) -> dict:
    return {
        "kind": weakness.kind.value,
        "name": weakness.name,
        "category": weakness.category.value if weakness.category else None,
        "description": weakness.description,
        "evidence": list(weakness.evidence),
    }


def _serialize_recommendation(recommendation: SkillRecommendation) -> dict:
    return {
        "skill": recommendation.skill,
        "category": recommendation.category.value,
        "reason": recommendation.reason,
        "based_on": list(recommendation.based_on),
        "chain": list(recommendation.chain),
    }


def aggregate_user_skills_detailed(repositories: list[dict]) -> PortfolioSkillReport:
    """
    Aggregate a user's per-repository technology detections and metadata
    analyses into a full portfolio-level skill report.

    Args:
        repositories: List of repository dicts; see the module docstring
            for the expected shape of each entry.

    Returns:
        A PortfolioSkillReport with every detected skill's SkillProfile
        (including derived composite skills, full evidence), its
        strengths and weaknesses subsets, and complementary-skill
        recommendations (possibly chained).
    """
    repository_data = _to_repository_skill_data(repositories)
    profiles = build_skill_profiles(repository_data)
    return PortfolioSkillReport(
        repository_count=len(repository_data),
        skills=tuple(profiles),
        strengths=tuple(detect_strengths(profiles)),
        weaknesses=tuple(detect_weaknesses(repository_data, profiles)),
        recommendations=tuple(generate_recommendations(profiles)),
    )


def aggregate_user_skills(repositories: list[dict]) -> dict:
    """
    Aggregate a user's per-repository technology detections and metadata
    analyses into a portfolio-level skill summary.

    This is the stable public API: the return value always has exactly
    the top-level keys below, regardless of internal engine changes.

    Args:
        repositories: List of repository dicts; see the module docstring
            for the expected shape of each entry.

    Returns:
        {
            "repository_count": int,
            "skills": [...],          # every detected skill (including
                                       # derived composites), score
                                       # descending then name
            "strengths": [...],       # subset of "skills" tiered
                                       # "proficient"/"expert"
            "weaknesses": [...],      # see below, three kinds, NOT the
                                       # same shape as "skills"/"strengths"
            "recommendations": [...], # missing complementary skills,
                                       # possibly chained
        }

        Each "skills"/"strengths" entry:
        {
            "name": str,                 # e.g. "Django", or "ESP32" for
                                          # a derived composite skill
            "category": str,
            "repository_count": int,
            "repositories": [str, ...],
            "average_detector_confidence": float,
            "average_practice_score": float,
            "score": int,                # see app.aggregator.rules for
                                          # the current breadth/confidence/
                                          # practice weighting
            "max_score": int,            # app.aggregator.rules.SKILL_MAX_SCORE
            "tier": "expert" | "proficient" | "developing" | "exposure",
            "evidence": [str, ...],      # explains exactly how "score"
                                          # was built, one line per
                                          # sub-score plus (for composites)
                                          # a line naming what it was
                                          # rolled up from
            "is_composite": bool,        # True for derived skills like
                                          # "ESP32"/"IoT"/"Embedded Systems"
        }

        Each "weaknesses" entry (one of three kinds, see
        app.aggregator.models.WeaknessKind):
        {
            "kind": "shallow_skill" | "limited_practice" | "limited_breadth",
            "name": str,                 # a skill name for "shallow_skill";
                                          # a human-readable label (e.g.
                                          # "CI/CD", "Frontend Breadth")
                                          # otherwise, NOT necessarily a
                                          # detectable technology name
            "category": str | None,      # None for "limited_practice"
                                          # (portfolio-wide, not tied to
                                          # one category)
            "description": str,
            "evidence": [str, ...],
        }

        Each "recommendations" entry:
        {
            "skill": str,
            "category": str,
            "reason": str,
            "based_on": [str, ...],      # established, actually-detected
                                          # root skill(s) this ultimately
                                          # traces back to
            "chain": [str, ...],         # hypothetical intermediate
                                          # skill(s) walked through but not
                                          # yet detected; empty for a
                                          # direct (1-hop) recommendation
        }
    """
    report = aggregate_user_skills_detailed(repositories)
    return {
        "repository_count": report.repository_count,
        "skills": [_serialize_skill(profile) for profile in report.skills],
        "strengths": [_serialize_skill(profile) for profile in report.strengths],
        "weaknesses": [_serialize_weakness(weakness) for weakness in report.weaknesses],
        "recommendations": [
            _serialize_recommendation(rec) for rec in report.recommendations
        ],
    }
