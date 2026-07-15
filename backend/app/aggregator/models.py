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
            (e.g. "detected in 3 repositories: api, cli, worker").
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
    A portfolio-level skill's overall depth, bucketed from its 0-7 point
    score. See app.aggregator.rules.tier_for_score() for the thresholds.
    """

    EXPERT = "expert"
    PROFICIENT = "proficient"
    DEVELOPING = "developing"
    EXPOSURE = "exposure"


@dataclass(frozen=True)
class SkillProfile:
    """
    Portfolio-level aggregation of one technology across every repository
    it was detected in.

    Attributes:
        name: Technology name, e.g. "Django".
        category: Ecosystem category (majority vote across occurrences;
            see app.aggregator.engine._majority_category()).
        repository_count: Number of distinct repositories this skill was
            detected in.
        repositories: Names of those repositories, sorted, for
            explainability.
        average_detector_confidence: Mean detector confidence across every
            occurrence of this skill.
        average_practice_score: Mean RepositoryPractice.score across every
            repository this skill was detected in.
        score: Total portfolio-level skill score (0-7); see
            app.aggregator.rules for how breadth, confidence, and practice
            combine.
        max_score: The rubric's maximum possible score (7).
        tier: The bucketed SkillTier for `score`.
        evidence: Human-readable breakdown of how `score` was built.
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


@dataclass(frozen=True)
class SkillRecommendation:
    """
    A suggested skill to learn next, based on a complementary-skill gap:
    the person has demonstrated an established skill whose usual pairing
    is absent from their portfolio entirely.

    Attributes:
        skill: The recommended technology's name.
        category: Its ecosystem category.
        reason: Human-readable explanation for the recommendation.
        based_on: Names of the established skill(s) that triggered this
            recommendation.
    """

    skill: str
    category: RuleCategory
    reason: str
    based_on: tuple[str, ...]


@dataclass(frozen=True)
class PortfolioSkillReport:
    """
    The complete output of the skill aggregation engine for one user's
    portfolio of repositories.

    Attributes:
        repository_count: Number of repositories the aggregation was
            computed over.
        skills: Every detected skill's SkillProfile, sorted by score
            descending then name.
        strengths: The subset of `skills` tiered PROFICIENT or EXPERT.
        weaknesses: The subset of `skills` tiered EXPOSURE (present, but
            with minimal supporting evidence).
        recommendations: Suggested skills to learn next, derived from
            complementary-skill gaps.
    """

    repository_count: int
    skills: tuple[SkillProfile, ...]
    strengths: tuple[SkillProfile, ...]
    weaknesses: tuple[SkillProfile, ...]
    recommendations: tuple[SkillRecommendation, ...]
