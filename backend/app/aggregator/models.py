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

from app.detector.models import EvidenceStrength, RuleCategory


@dataclass(frozen=True)
class TechnologyObservation:
    """
    One technology detected in one repository, i.e. a single element of
    app.detector.detector.detect_technologies_detailed()'s output.

    Attributes:
        name: Technology name, e.g. "Django".
        category: Ecosystem category from the detector's Rule.
        confidence: The detector's confidence for this match (0.0 - 1.0).
        evidence_strength: How strongly this occurrence proves actual use
            (declared / configured / demonstrated); see
            app.detector.models.EvidenceStrength. Defaults to
            DEMONSTRATED, unlike app.detector.models.Rule's identically-
            named field (which is required): this dataclass is part of
            app.aggregator.aggregator's public *input* contract (see that
            module's docstring -- callers may pass a plain 3-key dict with
            no evidence_strength at all), so forcing an explicit value
            here would break that existing, documented input shape.
            Defaulting to the strongest tier rather than the weakest is
            deliberate: an occurrence built by a caller that predates this
            field (or a test fixture unconcerned with evidence semantics)
            should not be silently discounted in new evidence-weighted
            scoring paths (see app.aggregator.rules.detection_confidence())
            it was never written with in mind.
    """

    name: str
    category: RuleCategory
    confidence: float
    evidence_strength: EvidenceStrength = EvidenceStrength.DEMONSTRATED

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

    Kept exactly as-is (same four members, same values) alongside the newer
    ProficiencyTier below rather than extended or renamed -- these values
    are serialized verbatim as SkillProfile.tier in the stable public API
    (see app.aggregator.aggregator.aggregate_user_skills()'s documented
    response shape), and nothing in that API is Pydantic-enforced, so a
    value change here would be a silent, non-compiler-caught breaking
    change for any existing API consumer. See ProficiencyTier's docstring
    for the additive, five-tier replacement and
    SKILL_TIER_DOWNGRADE_MAP (app.aggregator.rules) for how the two relate.
    """

    EXPERT = "expert"
    PROFICIENT = "proficient"
    DEVELOPING = "developing"
    EXPOSURE = "exposure"


class ProficiencyTier(str, Enum):
    """
    A finer-grained, five-level bucketing of a skill's depth, computed
    independently of (and in parallel with) the legacy four-level
    SkillTier above -- see app.aggregator.rules.proficiency_tier_for() for
    the exact criteria.

    Introduced alongside SkillProfile.detection_confidence as a
    genuinely-additive field: SkillProfile.tier/.score/
    .average_detector_confidence continue to be computed exactly as
    before, byte-for-byte, so no existing consumer of those fields is
    affected. proficiency_tier and detection_confidence are new fields on
    the same SkillProfile, computed via a parallel, evidence-strength-aware
    formula (see app.aggregator.rules.detection_confidence() and
    .proficiency_tier_for()).

    EXPOSURE:
        Weak/corroborating-only evidence, or a single declared-only
        occurrence with no demonstrated use at all.
    USED_ONCE:
        At least one DEMONSTRATED occurrence, but in exactly one
        repository, with low-to-no supporting engineering practice and
        insufficient combined breadth/confidence/practice to reach
        COMFORTABLE. Distinguishes "tried it for real, once" from mere
        EXPOSURE, a distinction the four-tier SkillTier collapses.
    COMFORTABLE:
        Real but modest depth: some demonstrated use with at least a
        little supporting practice, or repeated (2+) weaker-evidence
        occurrences.
    PROFICIENT:
        Solid, repeated, well-supported use.
    EXPERT:
        The strongest, most consistently well-supported use this rubric
        can currently express.

    Note (Phase 6 scope): this computation does not yet apply a recency
    factor (all occurrences are weighted as if equally current -- see the
    Phase 6 plan's decision 2.3, which defers per-signal recency to a
    later phase pending real commit-history ingestion) or an
    "advanced-signal" gate on EXPERT (see the v2 architecture document's
    3.4, explicitly out of scope until Phase 7). Both are real,
    intentional simplifications, not oversights.
    """

    EXPOSURE = "exposure"
    USED_ONCE = "used_once"
    COMFORTABLE = "comfortable"
    PROFICIENT = "proficient"
    EXPERT = "expert"


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
        tier: The bucketed SkillTier for `score`. Legacy four-tier field,
            computed exactly as before -- see `proficiency_tier` for the
            newer, additive five-tier alternative.
        detection_confidence: Evidence-strength-weighted mean detector
            confidence across every occurrence of this skill; see
            app.aggregator.rules.detection_confidence(). Distinct from
            `average_detector_confidence` (the plain, unweighted mean,
            kept unchanged for backward compatibility): this field
            discounts occurrences whose evidence_strength is DECLARED or
            CONFIGURED rather than DEMONSTRATED, so it is a more honest
            "how sure are we this is really here, and really used" signal.
            Equal to `average_detector_confidence` whenever every
            occurrence is DEMONSTRATED.
        proficiency_tier: The five-level ProficiencyTier for this skill,
            computed from `detection_confidence` (not
            `average_detector_confidence`) plus breadth and practice; see
            app.aggregator.rules.proficiency_tier_for(). Independent of,
            and not required to match, the legacy `tier` field.
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
    detection_confidence: float
    proficiency_tier: ProficiencyTier
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
