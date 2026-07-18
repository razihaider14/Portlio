"""
Deterministic rubrics and reference data for the skill aggregation engine.

Mirrors app.detector.rules (a flat, hand-curated, commented data table) and
the point-rubric style used by app.metadata.analyzers.documentation and
app.metadata.analyzers.maturity: every number below is either a count of an
exact, checkable fact, or a documented bucket boundary over such a count.
Nothing here is a tuned/opaque weight, and every rule carries its rationale
inline so a score can always be explained by pointing at the line that
produced it.

To change how a repository's practice score is computed, how a skill's
portfolio score/tier is derived, which composite skills get rolled up,
what counts as a soft weakness, or which skills are recommended together
(including chained, multi-hop recommendations): edit this file. No other
file needs to change, app.aggregator.engine reads these values generically.

Recalibration note (this revision): earlier versions of this rubric let
repository breadth alone push a skill to "expert" (e.g. plain HTML,
detected via file extension in 4 near-identical repositories, outscored
skills backed by real engineering discipline). This revision deliberately
caps breadth's contribution low and raises engineering practice's
contribution so that reaching "proficient"/"expert" now requires real
practice evidence (tests, CI/CD, docs, maturity, containerization), not
just showing up in a lot of repositories.
"""

from dataclasses import dataclass
from typing import Callable

from app.aggregator.models import SkillTier
from app.detector.models import RuleCategory

# Repository practice rubric
# One point per exact, checkable fact pulled straight from
# app.metadata.metadata_analyzer.analyze_repository_metadata()'s output.
# This score applies uniformly to every technology detected in that
# repository: a repository that tests, automates, documents, matures, and
# ships its code demonstrates that its technologies were exercised with
# real engineering discipline, not just present in a one-off snippet.
#
#   +1  has_tests is True
#   +1  has_ci_cd is True
#   +1  maturity.maturity_tier in {"active", "mature"} : i.e. the repo was
#       iterated on over a meaningful period, not a day-old dropped
#       experiment (see app.metadata.analyzers.maturity's tier rubric)
#   +1  documentation.quality_tier in {"good", "excellent"} : see
#       app.metadata.analyzers.documentation's 8-point rubric
#   +1  has_docker or has_kubernetes_manifests : packaged for deployment,
#       not just run locally
#
# Max score: 5. Unchanged by this revision: the *per-repository* rubric was
# never the problem, only how much weight its output carried at the
# portfolio level (see practice_points() below).
PRACTICE_MAX_SCORE = 5

_MATURE_TIERS = frozenset({"active", "mature"})
_DOCUMENTED_TIERS = frozenset({"good", "excellent"})

# Every practice fact above, paired with a human-readable label and a
# checker over a raw metadata dict. Reused for two purposes: computing
# score_repository_practice() above, and app.aggregator.engine's portfolio-
# wide "Limited X" weakness detection below (LIMITED_PRACTICE_THRESHOLD),
# so the exact same five facts are what both scoring and weakness detection
# look at, no separate, hand-picked subset for weaknesses.
PRACTICE_FACTS: tuple[tuple[str, Callable[[dict], bool]], ...] = (
    ("Testing", lambda metadata: bool(metadata.get("has_tests"))),
    ("CI/CD", lambda metadata: bool(metadata.get("has_ci_cd"))),
    (
        "Maturity",
        lambda metadata: (metadata.get("maturity") or {}).get("maturity_tier")
        in _MATURE_TIERS,
    ),
    (
        "Documentation",
        lambda metadata: (metadata.get("documentation") or {}).get("quality_tier")
        in _DOCUMENTED_TIERS,
    ),
    (
        "Containerization",
        lambda metadata: bool(
            metadata.get("has_docker") or metadata.get("has_kubernetes_manifests")
        ),
    ),
)


# Portfolio-level skill score rubric
# A technology's portfolio score sums three independent, bucketed counts:
# breadth (how many repositories), detection reliability (mean detector
# confidence), and engineering practice (mean per-repository practice
# score). Recalibrated weighting: breadth now contributes at most 2 of 8
# points (25%, down from 3 of 7 / 43%); practice now contributes at most 4
# of 8 (50%, up from 2 of 7 / 29%). A skill can no longer reach
# "proficient" or "expert" on breadth and confidence alone, see
# tier_for_score() below.
SKILL_MAX_SCORE = 8


# Breadth: how many distinct repositories use this skill, up to 2 points
# (previously up to 3). A single repository is still worth something (the
# skill is real), but repeated appearances across many repositories now
# earns no more credit than appearing in just two: real depth has to come
# from confidence and practice instead of sheer repetition, which is easy
# to rack up by copy-pasting the same small project structure.
#   1 repository   -> 1 point
#   2+ repositories -> 2 points (capped)
def breadth_points(repository_count: int) -> int:
    """Breadth sub-score (0-2) for the number of repositories a skill appears in."""
    if repository_count >= 2:
        return 2
    if repository_count >= 1:
        return 1
    return 0


# Detection reliability: mean detector confidence across every occurrence
# of the skill, up to 2 points (unchanged). Boundaries reuse the
# confidence scale already documented in app.detector.rules (1.0 = no
# false positives expected; 0.7-0.8 = a single reliable-but-not-exhaustive
# signal).
#   >= 0.9   -> 2 points (near-certain signal)
#   >= 0.75  -> 1 point  (reliable but not exhaustive signal)
#   <  0.75  -> 0 points (weak/heuristic signal)
def confidence_points(average_confidence: float) -> int:
    """Detection-reliability sub-score (0-2) for a skill's mean detector confidence."""
    if average_confidence >= 0.9:
        return 2
    if average_confidence >= 0.75:
        return 1
    return 0


# Engineering practice: mean RepositoryPractice.score (0-5, see above)
# across every repository the skill appears in, up to 4 points
# (previously up to 2). One portfolio point per whole practice-rubric
# point earned on average, capped at 4 (one point of headroom below the
# rubric's own max of 5, so breadth and confidence still have *some* say
# among otherwise-perfect-practice skills).
#   >= 4 of 5 practice points -> 4 points (near-maximal discipline)
#   >= 3 of 5 practice points -> 3 points
#   >= 2 of 5 practice points -> 2 points
#   >= 1 of 5 practice points -> 1 point
#   <  1 of 5 practice points -> 0 points (no supporting evidence at all)
def practice_points(average_practice_score: float) -> int:
    """Engineering-practice sub-score (0-4) for a skill's mean practice score."""
    if average_practice_score >= 4:
        return 4
    if average_practice_score >= 3:
        return 3
    if average_practice_score >= 2:
        return 2
    if average_practice_score >= 1:
        return 1
    return 0


# Skill tiers
# Buckets the 0-8 skill score, mirroring the threshold-table pattern in
# app.metadata.analyzers.documentation._TIER_THRESHOLDS. Checked in order;
# the first matching (highest) threshold wins.
#
# By construction, breadth (max 2) + confidence (max 2) = 4 points without
# any practice evidence at all, which only reaches DEVELOPING. Reaching
# PROFICIENT or EXPERT now requires real practice signal (score
# 2 or 4/5-average practice respectively, combined with at least some
# breadth/confidence), the exact gap the recalibration was asked to
# close.
_TIER_THRESHOLDS: tuple[tuple[int, SkillTier], ...] = (
    (7, SkillTier.EXPERT),
    (5, SkillTier.PROFICIENT),
    (2, SkillTier.DEVELOPING),
    (0, SkillTier.EXPOSURE),
)


def tier_for_score(score: int) -> SkillTier:
    """Map a 0-8 skill score to its SkillTier bucket."""
    for threshold, tier in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return SkillTier.EXPOSURE  # pragma: no cover - unreachable, thresholds start at 0


# Composite (derived) skills
@dataclass(frozen=True)
class CompositeSkillRule:
    """
    A portfolio-level skill derived by rolling up evidence from a group of
    related, directly-detected base technologies, for cases where the
    detector can identify the *toolchain* (e.g. Arduino sketches) but not
    the more specific thing built with it (e.g. that it targets an ESP32
    board), or where a broader capability (e.g. "Embedded Systems") is
    naturally the union of several narrower ones.

    Attributes:
        name: The composite skill's name, e.g. "ESP32".
        category: Its ecosystem category.
        base_technologies: Directly-detected skill names this composite
            rolls up evidence from. A repository counts toward this
            composite if it contains at least one of these.
        name_keywords: Optional case-insensitive substrings (matched
            against a normalized, alphanumeric-only repository name; see
            app.aggregator.engine._normalize_repository_name()). When
            given, only repositories whose name contains at least one
            keyword contribute evidence, this is how a specific,
            undetectable-from-file-contents-alone target (e.g. "this
            Arduino project is for an ESP32") gets corroborated: the
            detector can tell you the toolchain, the repository's own name
            is exact, checkable evidence of the specific target. An empty
            tuple means every repository with a qualifying base technology
            contributes (no further filtering).
        min_repositories: Minimum number of qualifying (and, if
            name_keywords is set, keyword-matching) repositories required
            for this composite to appear at all, "sufficient evidence".
            Below this, the composite is simply absent rather than shown
            at a low tier, since without name_keywords corroboration a
            single repository is often not enough to justify inventing a
            more specific skill than what was directly detected.
    """

    name: str
    category: RuleCategory
    base_technologies: tuple[str, ...]
    name_keywords: tuple[str, ...] = ()
    min_repositories: int = 1

    def __post_init__(self) -> None:
        if not self.base_technologies:
            raise ValueError(
                f"CompositeSkillRule '{self.name}': base_technologies must "
                "be non-empty"
            )
        if self.min_repositories < 1:
            raise ValueError(
                f"CompositeSkillRule '{self.name}': min_repositories must " "be >= 1"
            )


COMPOSITE_SKILL_RULES: tuple[CompositeSkillRule, ...] = (
    # The broad umbrella: any embedded/hardware toolchain at all. No
    # keyword filter, every repository with a qualifying base technology
    # contributes, since "Embedded Systems" doesn't claim any specific
    # target, just that embedded work happened.
    CompositeSkillRule(
        name="Embedded Systems",
        category=RuleCategory.EMBEDDED,
        base_technologies=("Arduino", "PlatformIO", "ESP-IDF", "PCB Design (Gerber)"),
    ),
    # ESP32 specifically: the detector can see Arduino/PlatformIO/ESP-IDF
    # tooling but has no way to tell which microcontroller a sketch
    # targets from file contents alone. A repository name that literally
    # says "esp32" is exact, checkable corroborating evidence of the
    # specific target, so it's used as a filter rather than a guess.
    CompositeSkillRule(
        name="ESP32",
        category=RuleCategory.EMBEDDED,
        base_technologies=("Arduino", "PlatformIO", "ESP-IDF"),
        name_keywords=("esp32", "esp-32", "esp_32"),
    ),
    # IoT: embedded work plus a name-level signal of networking/telemetry/
    # remote-sensing intent. Like ESP32 above, the detector has no rule
    # for "this talks MQTT" or "this reads a sensor", so the repository's
    # own name is used as corroborating evidence.
    CompositeSkillRule(
        name="IoT",
        category=RuleCategory.EMBEDDED,
        base_technologies=("Arduino", "PlatformIO", "ESP-IDF"),
        name_keywords=(
            "iot",
            "mqtt",
            "rpi",
            "raspberrypi",
            "wifi",
            "ble",
            "bluetooth",
            "sensor",
            "telemetry",
            "smarthome",
            "automation",
        ),
    ),
)

# Composite skill names, for quick membership checks elsewhere (e.g.
# excluding composites from the category-breadth weakness check below,
# since a derived roll-up shouldn't count as independent tooling
# diversity).
COMPOSITE_SKILL_NAMES: frozenset[str] = frozenset(
    rule.name for rule in COMPOSITE_SKILL_RULES
)


# Soft (portfolio-level) weaknesses
# A skill scored EXPOSURE is a "shallow skill" weakness (unchanged from
# the previous revision). But requiring EXPOSURE for *any* weakness to
# exist made weaknesses far too rare: a portfolio can be entirely free of
# barely-evidenced skills and still have real, portfolio-wide gaps (e.g.
# almost nothing has CI/CD). The two rules below add two further,
# independently-triggered kinds of weakness that don't depend on any
# single skill's tier; see WeaknessKind in app.aggregator.models.

# LIMITED_PRACTICE: for each of the five PRACTICE_FACTS above, look at
# every repository in the portfolio (not just ones with a given skill) and
# compute what fraction exhibits that fact. Below half is "the exception,
# not the norm" for that portfolio, an intuitive, easy-to-defend
# midpoint rather than a tuned threshold.
LIMITED_PRACTICE_THRESHOLD = 0.5

# Below three repositories, a fraction is too noisy to fairly call
# "limited" (e.g. 0-of-1 is just as easily "haven't gotten to it yet" as
# an actual pattern). Matches the smallest bucket size discussed
# elsewhere in this module (breadth's own first bucket is 1 repository;
# three is the point where a fraction starts being a real sample).
MIN_REPOSITORIES_FOR_PRACTICE_JUDGEMENT = 3

# LIMITED_BREADTH: an ecosystem category represented by exactly one
# directly-detected technology (composite/derived skills don't count,
# see COMPOSITE_SKILL_NAMES) despite a meaningful combined repository
# footprint suggests the person has only ever reached for one tool in
# that category. Same repository-count floor as practice judgements, for
# the same reason.
MIN_REPOSITORIES_FOR_BREADTH_JUDGEMENT = 3


# Complementary skill registry (drives recommendations)
@dataclass(frozen=True)
class ComplementRule:
    """
    One hand-curated pairing: if `trigger` is an established skill in the
    portfolio (tier above EXPOSURE) and none of `complements` is present at
    all, recommend `recommended`.

    `trigger` need not be an established, directly-detected skill: it can
    also be another rule's `recommended` skill, in which case chaining
    applies, see app.aggregator.engine.generate_recommendations() and
    MAX_RECOMMENDATION_CHAIN_DEPTH below. This is what allows a suggested
    learning path like ESP32 -> FreeRTOS -> ESP-IDF: the ESP32 -> FreeRTOS
    rule's `recommended` ("FreeRTOS") is also the FreeRTOS -> ESP-IDF
    rule's `trigger`.

    Attributes:
        trigger: Skill name that activates this rule when established (or,
            for chaining, when reached as a prior hop's recommendation).
        complements: Every skill name that would satisfy this pairing
            (checked for presence at any tier). Must include `recommended`.
        recommended: The specific skill to suggest when the pairing is
            entirely missing.
        category: The recommended skill's ecosystem category.
        reason: Human-readable explanation shown with the recommendation.
    """

    trigger: str
    complements: tuple[str, ...]
    recommended: str
    category: RuleCategory
    reason: str

    def __post_init__(self) -> None:
        if self.recommended not in self.complements:
            raise ValueError(
                f"ComplementRule for '{self.trigger}': recommended skill "
                f"'{self.recommended}' must be one of complements "
                f"{self.complements}"
            )


# Recommendations may chain up to this many hops beyond the established,
# actually-detected root skill (root -> hop 1 -> hop 2 with the default of
# 2). Kept small and explicit: a 2-hop learning path ("ESP32 -> FreeRTOS ->
# ESP-IDF") is a useful suggestion; an unbounded walk would eventually
# produce a speculative curriculum several steps removed from anything the
# person has actually demonstrated.
MAX_RECOMMENDATION_CHAIN_DEPTH = 2

COMPLEMENT_RULES: tuple[ComplementRule, ...] = (
    # Python web frameworks without a Python test runner
    ComplementRule(
        trigger="Django",
        complements=("pytest",),
        recommended="pytest",
        category=RuleCategory.TESTING,
        reason=(
            "Django is an established skill, but no Python testing "
            "framework was detected. pytest is the de facto standard for "
            "testing Django projects."
        ),
    ),
    ComplementRule(
        trigger="Flask",
        complements=("pytest",),
        recommended="pytest",
        category=RuleCategory.TESTING,
        reason=(
            "Flask is an established skill, but no Python testing "
            "framework was detected. pytest pairs naturally with Flask's "
            "built-in test client."
        ),
    ),
    ComplementRule(
        trigger="FastAPI",
        complements=("pytest",),
        recommended="pytest",
        category=RuleCategory.TESTING,
        reason=(
            "FastAPI is an established skill, but no Python testing "
            "framework was detected. pytest is the standard companion for "
            "testing FastAPI's dependency-injected endpoints."
        ),
    ),
    # Python without any static analysis tool
    ComplementRule(
        trigger="Python",
        complements=("Ruff", "Flake8", "Pylint", "mypy"),
        recommended="Ruff",
        category=RuleCategory.STATIC_ANALYSIS,
        reason=(
            "Python is an established skill, but no linter or static "
            "analysis tool was detected. Ruff is a fast, widely-adopted "
            "standard for Python projects."
        ),
    ),
    # Chain hop: Ruff without CI to enforce it on every push
    ComplementRule(
        trigger="Ruff",
        complements=(
            "GitHub Actions",
            "GitLab CI",
            "CircleCI",
            "Travis CI",
            "Jenkins",
            "Drone CI",
            "Buildkite",
            "Azure Pipelines",
            "Bitbucket Pipelines",
            "Google Cloud Build",
        ),
        recommended="GitHub Actions",
        category=RuleCategory.CI_CD,
        reason=(
            "Ruff is a natural next step after Python, and wiring it into "
            "CI (e.g. GitHub Actions) is what makes it actually enforced "
            "on every push rather than run ad hoc."
        ),
    ),
    # JS/TS frameworks without a JS/TS test runner
    ComplementRule(
        trigger="React",
        complements=("Jest", "Vitest", "Cypress", "Playwright"),
        recommended="Jest",
        category=RuleCategory.TESTING,
        reason=(
            "React is an established skill, but no JavaScript/TypeScript "
            "test runner was detected. Jest is the most common pairing "
            "for React component testing."
        ),
    ),
    ComplementRule(
        trigger="Express",
        complements=("Jest", "Mocha", "Vitest"),
        recommended="Jest",
        category=RuleCategory.TESTING,
        reason=(
            "Express is an established skill, but no JavaScript test "
            "runner was detected. Jest is the most common choice for "
            "testing Express APIs."
        ),
    ),
    ComplementRule(
        trigger="NestJS",
        complements=("Jest",),
        recommended="Jest",
        category=RuleCategory.TESTING,
        reason=(
            "NestJS is an established skill, but Jest (NestJS's default, "
            "scaffolded test runner) was not detected."
        ),
    ),
    # TypeScript without a linter
    ComplementRule(
        trigger="TypeScript",
        complements=("ESLint",),
        recommended="ESLint",
        category=RuleCategory.STATIC_ANALYSIS,
        reason=(
            "TypeScript is an established skill, but ESLint, the standard "
            "linter for the TypeScript ecosystem, was not detected."
        ),
    ),
    # Other language ecosystems without their standard test framework
    ComplementRule(
        trigger="Ruby on Rails",
        complements=("RSpec",),
        recommended="RSpec",
        category=RuleCategory.TESTING,
        reason=(
            "Ruby on Rails is an established skill, but RSpec, the "
            "ecosystem's most widely used testing framework, was not "
            "detected."
        ),
    ),
    ComplementRule(
        trigger="Spring Boot",
        complements=("JUnit",),
        recommended="JUnit",
        category=RuleCategory.TESTING,
        reason=(
            "Spring Boot is an established skill, but JUnit, the standard "
            "Java testing framework, was not detected."
        ),
    ),
    ComplementRule(
        trigger="Laravel",
        complements=("PHPUnit",),
        recommended="PHPUnit",
        category=RuleCategory.TESTING,
        reason=(
            "Laravel is an established skill, but PHPUnit, the standard "
            "PHP testing framework, was not detected."
        ),
    ),
    # Backend languages without a web framework
    ComplementRule(
        trigger="Go",
        complements=("Gin", "Echo", "Fiber"),
        recommended="Gin",
        category=RuleCategory.FRAMEWORK,
        reason=(
            "Go is an established skill, but no Go web framework was "
            "detected. Gin is the most widely adopted lightweight "
            "framework for building Go APIs."
        ),
    ),
    ComplementRule(
        trigger="Rust",
        complements=("Actix Web", "Rocket"),
        recommended="Actix Web",
        category=RuleCategory.FRAMEWORK,
        reason=(
            "Rust is an established skill, but no Rust web framework was "
            "detected. Actix Web is one of the most widely adopted "
            "options for building Rust web services."
        ),
    ),
    # Containerization without orchestration or Compose
    ComplementRule(
        trigger="Docker",
        complements=("Docker Compose", "Kubernetes", "Helm"),
        recommended="Docker Compose",
        category=RuleCategory.CONTAINER,
        reason=(
            "Docker is an established skill, but neither Docker Compose "
            "nor an orchestration tool was detected. Compose is the "
            "natural next step for running multi-container setups "
            "locally."
        ),
    ),
    ComplementRule(
        trigger="Kubernetes",
        complements=("Helm",),
        recommended="Helm",
        category=RuleCategory.ORCHESTRATION,
        reason=(
            "Kubernetes is an established skill, but Helm, the standard "
            "package manager for templating and managing Kubernetes "
            "manifests, was not detected."
        ),
    ),
    # Infrastructure provisioning without configuration management
    ComplementRule(
        trigger="Terraform",
        complements=("Ansible",),
        recommended="Ansible",
        category=RuleCategory.DEVOPS,
        reason=(
            "Terraform is an established skill, but Ansible, a common "
            "pairing for post-provisioning configuration management, was "
            "not detected."
        ),
    ),
    # Test frameworks without any CI/CD provider to run them
    ComplementRule(
        trigger="pytest",
        complements=(
            "GitHub Actions",
            "GitLab CI",
            "CircleCI",
            "Travis CI",
            "Jenkins",
            "Drone CI",
            "Buildkite",
            "Azure Pipelines",
            "Bitbucket Pipelines",
            "Google Cloud Build",
        ),
        recommended="GitHub Actions",
        category=RuleCategory.CI_CD,
        reason=(
            "pytest is an established skill, but no CI/CD provider was "
            "detected. GitHub Actions is the most common way to "
            "automatically run a Python test suite on every push."
        ),
    ),
    ComplementRule(
        trigger="Jest",
        complements=(
            "GitHub Actions",
            "GitLab CI",
            "CircleCI",
            "Travis CI",
            "Jenkins",
            "Drone CI",
            "Buildkite",
            "Azure Pipelines",
            "Bitbucket Pipelines",
            "Google Cloud Build",
        ),
        recommended="GitHub Actions",
        category=RuleCategory.CI_CD,
        reason=(
            "Jest is an established skill, but no CI/CD provider was "
            "detected. GitHub Actions is the most common way to "
            "automatically run a JavaScript/TypeScript test suite on "
            "every push."
        ),
    ),
    # Embedded/IoT chain: ESP32 -> FreeRTOS -> ESP-IDF
    ComplementRule(
        trigger="ESP32",
        complements=("FreeRTOS",),
        recommended="FreeRTOS",
        category=RuleCategory.EMBEDDED,
        reason=(
            "ESP32 is an established skill, but FreeRTOS, the "
            "real-time OS most ESP32 projects build on once they outgrow "
            "simple Arduino sketches, was not detected."
        ),
    ),
    ComplementRule(
        trigger="FreeRTOS",
        complements=("ESP-IDF",),
        recommended="ESP-IDF",
        category=RuleCategory.EMBEDDED,
        reason=(
            "FreeRTOS is a natural next step, and ESP-IDF (Espressif's "
            "official SDK, built directly on FreeRTOS) is the standard "
            "way to use it beyond the Arduino abstraction layer."
        ),
    ),
)
