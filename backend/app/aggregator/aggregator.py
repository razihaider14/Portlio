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
"""

from app.aggregator.engine import (
    build_skill_profiles,
    detect_strengths,
    detect_weaknesses,
    generate_recommendations,
)
from app.aggregator.models import (
    PortfolioSkillReport,
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
    }


def _serialize_recommendation(recommendation: SkillRecommendation) -> dict:
    return {
        "skill": recommendation.skill,
        "category": recommendation.category.value,
        "reason": recommendation.reason,
        "based_on": list(recommendation.based_on),
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
        (including full evidence), its strengths and weaknesses subsets,
        and complementary-skill recommendations.
    """
    repository_data = _to_repository_skill_data(repositories)
    profiles = build_skill_profiles(repository_data)
    return PortfolioSkillReport(
        repository_count=len(repository_data),
        skills=tuple(profiles),
        strengths=tuple(detect_strengths(profiles)),
        weaknesses=tuple(detect_weaknesses(profiles)),
        recommendations=tuple(generate_recommendations(profiles)),
    )


def aggregate_user_skills(repositories: list[dict]) -> dict:
    """
    Aggregate a user's per-repository technology detections and metadata
    analyses into a portfolio-level skill summary.

    This is the stable public API: the return value always has exactly
    the keys below, regardless of internal engine changes.

    Args:
        repositories: List of repository dicts; see the module docstring
            for the expected shape of each entry.

    Returns:
        {
            "repository_count": int,
            "skills": [...],          # every detected skill, score descending
            "strengths": [...],       # subset tiered "proficient"/"expert"
            "weaknesses": [...],      # subset tiered "exposure"
            "recommendations": [...], # missing complementary skills
        }
        Each skill entry mirrors SkillProfile's fields (JSON-friendly,
        enums as their string value). Each recommendation entry mirrors
        SkillRecommendation's fields.
    """
    report = aggregate_user_skills_detailed(repositories)
    return {
        "repository_count": report.repository_count,
        "skills": [_serialize_skill(profile) for profile in report.skills],
        "strengths": [_serialize_skill(profile) for profile in report.strengths],
        "weaknesses": [_serialize_skill(profile) for profile in report.weaknesses],
        "recommendations": [
            _serialize_recommendation(rec) for rec in report.recommendations
        ],
    }
