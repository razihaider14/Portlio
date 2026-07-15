"""
Skill aggregation engine.

Mirrors app.detector.engine / app.metadata.engine: pure functions over
already-computed inputs, with no knowledge of GitHub, HTTP, application
state, or how RepositorySkillData was produced. No side effects, no AI,
fully deterministic, straightforward to test in isolation.

Pipeline:
    1. score_repository_practice() : one repository's metadata -> a 0-5
       RepositoryPractice score (see app.aggregator.rules).
    2. build_skill_profiles() : every repository's technologies +
       practice scores -> one SkillProfile per distinct technology,
       aggregated across the whole portfolio.
    3. detect_strengths() / detect_weaknesses() : filter SkillProfiles by
       SkillTier.
    4. generate_recommendations() : compare established skills against
       app.aggregator.rules.COMPLEMENT_RULES to find missing pairings.
"""

from collections import Counter, defaultdict
from statistics import mean

from app.aggregator.models import (
    RepositoryPractice,
    RepositorySkillData,
    SkillProfile,
    SkillRecommendation,
    SkillTier,
    TechnologyObservation,
)
from app.aggregator.rules import (
    COMPLEMENT_RULES,
    PRACTICE_MAX_SCORE,
    SKILL_MAX_SCORE,
    ComplementRule,
    _DOCUMENTED_TIERS,
    _MATURE_TIERS,
    breadth_points,
    confidence_points,
    practice_points,
    tier_for_score,
)
from app.detector.models import RuleCategory


def score_repository_practice(metadata: dict) -> RepositoryPractice:
    """
    Compute the 0-5 engineering-practice score for one repository from its
    app.metadata.metadata_analyzer.analyze_repository_metadata() output.
    See app.aggregator.rules for the point rubric. Missing keys degrade to
    "no evidence" (0 points for that line) rather than raising, since
    metadata may be partially unavailable (e.g. no repo_metadata fetched).
    """
    evidence: list[str] = []
    score = 0

    if metadata.get("has_tests"):
        score += 1
        evidence.append("has an identifiable test suite")

    if metadata.get("has_ci_cd"):
        score += 1
        evidence.append("has CI/CD configured")

    maturity_tier = (metadata.get("maturity") or {}).get("maturity_tier")
    if maturity_tier in _MATURE_TIERS:
        score += 1
        evidence.append(f"maturity tier is '{maturity_tier}'")

    doc_tier = (metadata.get("documentation") or {}).get("quality_tier")
    if doc_tier in _DOCUMENTED_TIERS:
        score += 1
        evidence.append(f"documentation quality tier is '{doc_tier}'")

    if metadata.get("has_docker") or metadata.get("has_kubernetes_manifests"):
        score += 1
        evidence.append("packaged for containerized deployment")

    return RepositoryPractice(
        score=score, max_score=PRACTICE_MAX_SCORE, evidence=tuple(evidence)
    )


def _majority_category(categories: list[RuleCategory]) -> RuleCategory:
    """
    The most common category among a skill's occurrences. Ties are broken
    by the category's enum value (alphabetical), for a fully deterministic
    result. In practice a technology's category is fixed by a single
    detector Rule, so this only matters if RULES ever assigns the same
    name two different categories.
    """
    counts = Counter(categories)
    max_count = max(counts.values())
    candidates = sorted(
        (category for category, count in counts.items() if count == max_count),
        key=lambda category: category.value,
    )
    return candidates[0]


def build_skill_profiles(
    repositories: list[RepositorySkillData],
) -> list[SkillProfile]:
    """
    Aggregate every repository's detected technologies into one
    SkillProfile per distinct technology name, scored across the whole
    portfolio. See app.aggregator.rules for the scoring rubric.

    Args:
        repositories: One RepositorySkillData per repository, combining
            the detector's and metadata analyzer's output for that repo.

    Returns:
        One SkillProfile per distinct technology name detected in any
        repository, sorted by score descending then name ascending.
    """
    occurrences: dict[
        str, list[tuple[str, TechnologyObservation, RepositoryPractice]]
    ] = defaultdict(list)
    for repo in repositories:
        practice = score_repository_practice(repo.metadata)
        for tech in repo.technologies:
            occurrences[tech.name].append((repo.name, tech, practice))

    profiles: list[SkillProfile] = []
    for name, entries in occurrences.items():
        repo_names = tuple(sorted({repo_name for repo_name, _, _ in entries}))
        repository_count = len(repo_names)

        average_confidence = mean(tech.confidence for _, tech, _ in entries)
        average_practice = mean(practice.score for _, _, practice in entries)
        category = _majority_category([tech.category for _, tech, _ in entries])

        breadth = breadth_points(repository_count)
        confidence_score = confidence_points(average_confidence)
        practice_score = practice_points(average_practice)
        total_score = breadth + confidence_score + practice_score

        evidence = (
            f"detected in {repository_count} "
            f"repositor{'y' if repository_count == 1 else 'ies'} "
            f"({breadth} breadth point{'s' if breadth != 1 else ''})",
            f"average detection confidence {average_confidence:.2f} "
            f"({confidence_score} point{'s' if confidence_score != 1 else ''})",
            f"average engineering-practice score "
            f"{average_practice:.1f}/{PRACTICE_MAX_SCORE} "
            f"({practice_score} point{'s' if practice_score != 1 else ''})",
        )

        profiles.append(
            SkillProfile(
                name=name,
                category=category,
                repository_count=repository_count,
                repositories=repo_names,
                average_detector_confidence=average_confidence,
                average_practice_score=average_practice,
                score=total_score,
                max_score=SKILL_MAX_SCORE,
                tier=tier_for_score(total_score),
                evidence=evidence,
            )
        )

    return sorted(profiles, key=lambda profile: (-profile.score, profile.name))


def detect_strengths(profiles: list[SkillProfile]) -> list[SkillProfile]:
    """
    Skills tiered PROFICIENT or EXPERT: repeated, reliably-detected use
    backed by real engineering practice. Sorted by score descending then
    name.
    """
    strengths = [
        profile
        for profile in profiles
        if profile.tier in (SkillTier.EXPERT, SkillTier.PROFICIENT)
    ]
    return sorted(strengths, key=lambda profile: (-profile.score, profile.name))


def detect_weaknesses(profiles: list[SkillProfile]) -> list[SkillProfile]:
    """
    Skills tiered EXPOSURE: present in the portfolio, but with minimal
    supporting evidence (typically a single repository, low detection
    confidence, and/or no engineering-practice signals). This is distinct
    from a skill being entirely absent, which is not a weakness but a
    candidate for app.aggregator.rules.COMPLEMENT_RULES-driven
    recommendations instead. Sorted by score ascending then name.
    """
    weaknesses = [profile for profile in profiles if profile.tier == SkillTier.EXPOSURE]
    return sorted(weaknesses, key=lambda profile: (profile.score, profile.name))


def generate_recommendations(
    profiles: list[SkillProfile],
) -> list[SkillRecommendation]:
    """
    Recommend missing complementary skills for every established skill
    (tier above EXPOSURE) whose usual pairing is entirely absent from the
    portfolio, using the curated app.aggregator.rules.COMPLEMENT_RULES
    table. A single accidental, low-confidence, single-repository
    detection does not trigger a recommendation (it isn't yet
    "established"), avoiding noisy suggestions.

    If multiple established skills recommend the same missing skill, the
    recommendation is merged (`based_on` lists every triggering skill).

    Returns:
        Recommendations sorted by the strongest triggering skill's score
        descending, then by recommended skill name.
    """
    scores_by_name = {profile.name: profile.score for profile in profiles}
    present = set(scores_by_name)
    established = {
        profile.name for profile in profiles if profile.tier != SkillTier.EXPOSURE
    }

    based_on_by_skill: dict[str, list[str]] = defaultdict(list)
    rule_by_skill: dict[str, ComplementRule] = {}

    for rule in COMPLEMENT_RULES:
        if rule.trigger not in established:
            continue
        if any(complement in present for complement in rule.complements):
            continue
        based_on_by_skill[rule.recommended].append(rule.trigger)
        rule_by_skill[rule.recommended] = rule

    recommendations = [
        SkillRecommendation(
            skill=skill,
            category=rule_by_skill[skill].category,
            reason=rule_by_skill[skill].reason,
            based_on=tuple(sorted(based_on)),
        )
        for skill, based_on in based_on_by_skill.items()
    ]

    return sorted(
        recommendations,
        key=lambda rec: (
            -max(scores_by_name[trigger] for trigger in rec.based_on),
            rec.skill,
        ),
    )
