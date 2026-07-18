"""
Core data models for the skill aggregation engine.

Mirrors app.detector.models / app.metadata.models in spirit: small typed
inputs, a pure engine over them, and richly-typed results. Unlike
app.metadata (which is deliberately independent of app.detector), the
aggregator's whole purpose is to consume both subsystems' outputs, so it
imports app.detector.models.RuleCategory directly rather than redefining
it. It does not import from app.metadata: metadata's output is consumed as
the plain, stable dict shape returned by
app.metadata.metadata_analyzer.analyze_repository_metadata(), which is
already that subsystem's public contract.
"""

from dataclasses import dataclass, field
from enum import Enum

from app.detector.models import RuleCategory


@dataclass(frozen=True)
class TechnologyObservation:
    """
    One technology detected in one repository, i.e. a single element of
    app.detector.detector.detect_technologies_detailed()'s output.

    Attributes:
        name: Technology name, e.g. "Django".
        category: Ecosystem category from the detector's Rule.
        confidence: The detector's confidence for this match (0.0 - 1.0).
    """

    name: str
    category: RuleCategory
    confidence: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"TechnologyObservation '{self.name}': confidence must be "
                f"between 0.0 and 1.0, got {self.confidence}"
            )


@dataclass(frozen=True)
class RepositorySkillData:
    """
    Everything the aggregator is allowed to look at for one repository: the
    technology detector's and the metadata analyzer's combined output.
    Deliberately plain (a tuple of TechnologyObservation and a dict) so the
    aggregator never has to reach back into raw file trees.

    Attributes:
        name: Repository name, used only for evidence/explainability
            (e.g. "detected in 3 repositories: api, cli, worker") and as
            corroborating evidence for derived/composite skills (see
            app.aggregator.rules.COMPOSITE_SKILL_RULES).
        technologies: Every technology the detector found in this
            repository.
        metadata: The dict returned by
            app.metadata.metadata_analyzer.analyze_repository_metadata()
            for this repository. Treated as optional/possibly-empty;
            missing keys degrade to "no evidence", never raise.
    """

    name: str
    technologies: tuple[TechnologyObservation, ...] = ()
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RepositoryPractice:
    """
    The engineering-practice rubric score computed for one repository from
    its metadata. Applies uniformly to every technology detected in that
    repository, since the underlying facts (tests, CI/CD, maturity, docs,
    containerization) describe how the whole repository was built, not any
    single technology within it. See app.aggregator.rules for the rubric.

    Attributes:
        score: Points earned, 0 to max_score.
        max_score: The rubric's maximum possible score.
        evidence: Human-readable reasons for each point earned.
    """

    score: int
    max_score: int
    evidence: tuple[str, ...] = ()


class SkillTier(str, Enum):
    """
    A portfolio-level skill's overall depth, bucketed from its point score.
    See app.aggregator.rules.tier_for_score() for the thresholds and
    app.aggregator.rules.SKILL_MAX_SCORE for the current maximum.
    """

    EXPERT = "expert"
    PROFICIENT = "proficient"
    DEVELOPING = "developing"
    EXPOSURE = "exposure"


@dataclass(frozen=True)
class SkillProfile:
    """
    Portfolio-level aggregation of one technology across every repository
    it was detected in. May represent either a technology the detector
    found directly, or a derived/composite skill (e.g. "ESP32", "IoT",
    "Embedded Systems") rolled up from a group of related directly-detected
    technologies; see app.aggregator.rules.COMPOSITE_SKILL_RULES. Composite
    profiles are scored with the exact same rubric as directly-detected
    ones and are indistinguishable in shape, only their evidence text
    notes that they were derived.

    Attributes:
        name: Technology (or composite skill) name, e.g. "Django", "ESP32".
        category: Ecosystem category (majority vote across occurrences;
            see app.aggregator.engine._majority_category()).
        repository_count: Number of distinct repositories this skill was
            detected in (or, for composite skills, the number of
            repositories contributing qualifying evidence).
        repositories: Names of those repositories, sorted, for
            explainability.
        average_detector_confidence: Mean detector confidence across every
            occurrence of this skill.
        average_practice_score: Mean RepositoryPractice.score across every
            repository this skill was detected in.
        score: Total portfolio-level skill score; see
            app.aggregator.rules for how breadth, confidence, and practice
            combine.
        max_score: The rubric's maximum possible score; see
            app.aggregator.rules.SKILL_MAX_SCORE.
        tier: The bucketed SkillTier for `score`.
        evidence: Human-readable breakdown of how `score` was built.
        is_composite: True if this skill was derived from other detected
            technologies (see app.aggregator.rules.COMPOSITE_SKILL_RULES)
            rather than detected directly by app.detector.
    """

    name: str
    category: RuleCategory
    repository_count: int
    repositories: tuple[str, ...]
    average_detector_confidence: float
    average_practice_score: float
    score: int
    max_score: int
    tier: SkillTier
    evidence: tuple[str, ...] = ()
    is_composite: bool = False


class WeaknessKind(str, Enum):
    """
    What kind of gap a PortfolioWeakness describes.

    SHALLOW_SKILL: a specific detected skill with minimal supporting
        evidence (SkillTier.EXPOSURE): usually a single repository, low
        detector confidence, and/or no engineering-practice signals.
    LIMITED_PRACTICE: a portfolio-wide engineering-practice gap, e.g. most
        repositories lack CI/CD or tests. Not tied to any one skill.
    LIMITED_BREADTH: a whole ecosystem category represented by only a
        single technology despite a meaningful repository footprint, e.g.
        "Limited Frontend Breadth" when every frontend repository only
        ever uses plain HTML.
    """

    SHALLOW_SKILL = "shallow_skill"
    LIMITED_PRACTICE = "limited_practice"
    LIMITED_BREADTH = "limited_breadth"


@dataclass(frozen=True)
class PortfolioWeakness:
    """
    One portfolio-level gap or soft weakness. See WeaknessKind for the
    three kinds this can represent; app.aggregator.rules documents the
    exact, deterministic conditions that produce each one.

    Attributes:
        kind: Which WeaknessKind this is.
        name: For SHALLOW_SKILL, the skill's name (e.g. "Cobol"). For
            LIMITED_PRACTICE/LIMITED_BREADTH, a human-readable label (e.g.
            "CI/CD", "Frontend Breadth"), NOT necessarily a detectable
            technology name.
        category: The relevant RuleCategory, when there is one
            (SHALLOW_SKILL's own category, or LIMITED_BREADTH's category).
            None for LIMITED_PRACTICE, which is portfolio-wide rather than
            category-specific.
        description: Human-readable explanation of the gap.
        evidence: Supporting details (e.g. the specific repositories
            lacking the practice, or the score breakdown for a shallow
            skill).
    """

    kind: WeaknessKind
    name: str
    category: RuleCategory | None
    description: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillRecommendation:
    """
    A suggested skill to learn next, based on a complementary-skill gap:
    the person has demonstrated an established skill whose usual pairing
    is absent from their portfolio entirely. Recommendations can chain:
    see app.aggregator.rules.MAX_RECOMMENDATION_CHAIN_DEPTH and
    app.aggregator.engine.generate_recommendations().

    Attributes:
        skill: The recommended technology's name.
        category: Its ecosystem category.
        reason: Human-readable explanation for the recommendation.
        based_on: Names of the established, actually-detected skill(s)
            this recommendation ultimately traces back to.
        chain: The hypothetical intermediate skill(s), not yet detected in
            the portfolio, walked through to reach this recommendation.
            Empty when this recommendation follows directly from an
            established skill. E.g. for a recommendation of "ESP-IDF"
            reached via established "ESP32" -> "FreeRTOS" -> "ESP-IDF",
            based_on=("ESP32",) and chain=("FreeRTOS",).
    """

    skill: str
    category: RuleCategory
    reason: str
    based_on: tuple[str, ...]
    chain: tuple[str, ...] = ()


@dataclass(frozen=True)
class PortfolioSkillReport:
    """
    The complete output of the skill aggregation engine for one user's
    portfolio of repositories.

    Attributes:
        repository_count: Number of repositories the aggregation was
            computed over.
        skills: Every detected skill's SkillProfile (including derived
            composite skills), sorted by score descending then name.
        strengths: The subset of `skills` tiered PROFICIENT or EXPERT.
        weaknesses: Portfolio gaps and soft weaknesses; see
            WeaknessKind and app.aggregator.rules for exactly what
            triggers each kind.
        recommendations: Suggested skills to learn next, derived from
            complementary-skill gaps, possibly chained across more than
            one hop.
    """

    repository_count: int
    skills: tuple[SkillProfile, ...]
    strengths: tuple[SkillProfile, ...]
    weaknesses: tuple[PortfolioWeakness, ...]
    recommendations: tuple[SkillRecommendation, ...]
