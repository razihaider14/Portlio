"""
Deterministic rubrics and reference data for the skill aggregation engine.

Mirrors app.detector.rules (a flat, hand-curated, commented data table) and
the point-rubric style used by app.metadata.analyzers.documentation and
app.metadata.analyzers.maturity: every number below is either a count of an
exact, checkable fact, or a documented bucket boundary over such a count.
Nothing here is a tuned/opaque weight, and every rule carries its rationale
inline so a score can always be explained by pointing at the line that
produced it.

To change how a repository's practice score is computed, or how a skill's
portfolio score/tier is derived, or which skills are recommended together:
edit this file. No other file needs to change, app.aggregator.engine reads
these values generically.
"""

from dataclasses import dataclass, field

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
# Max score: 5.
PRACTICE_MAX_SCORE = 5

_MATURE_TIERS = frozenset({"active", "mature"})
_DOCUMENTED_TIERS = frozenset({"good", "excellent"})


# Portfolio-level skill score rubric
# A technology's 0-7 point portfolio score sums three independent,
# bucketed counts. Each sub-score buckets a countable fact into a small
# number of documented tiers, the same "point rubric -> tier table"
# pattern used throughout app.metadata.analyzers.
#
# Breadth: how many distinct repositories use this skill, up to 3 points.
#   1 repository      -> 1 point  (used, but only once)
#   2-3 repositories   -> 2 points (used more than once)
#   4+ repositories    -> 3 points (used repeatedly across the portfolio)
SKILL_MAX_SCORE = 7


def breadth_points(repository_count: int) -> int:
    """Breadth sub-score (0-3) for the number of repositories a skill appears in."""
    if repository_count >= 4:
        return 3
    if repository_count >= 2:
        return 2
    if repository_count >= 1:
        return 1
    return 0


# Detection reliability: mean detector confidence across every occurrence
# of the skill, up to 2 points. Boundaries reuse the confidence scale
# already documented in app.detector.rules (1.0 = no false positives
# expected; 0.7-0.8 = a single reliable-but-not-exhaustive signal).
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
# across every repository the skill appears in, up to 2 points.
#   >= 4 of 5 practice points -> 2 points (consistently well-engineered)
#   >= 2 of 5 practice points -> 1 point  (some engineering discipline)
#   <  2 of 5 practice points -> 0 points (little to no supporting evidence)
def practice_points(average_practice_score: float) -> int:
    """Engineering-practice sub-score (0-2) for a skill's mean practice score."""
    if average_practice_score >= 4:
        return 2
    if average_practice_score >= 2:
        return 1
    return 0


# Skill tiers
# Buckets the 0-7 skill score, mirroring the threshold-table pattern in
# app.metadata.analyzers.documentation._TIER_THRESHOLDS. Checked in order;
# the first matching (highest) threshold wins.
_TIER_THRESHOLDS: tuple[tuple[int, SkillTier], ...] = (
    (6, SkillTier.EXPERT),
    (4, SkillTier.PROFICIENT),
    (2, SkillTier.DEVELOPING),
    (0, SkillTier.EXPOSURE),
)


def tier_for_score(score: int) -> SkillTier:
    """Map a 0-7 skill score to its SkillTier bucket."""
    for threshold, tier in _TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return SkillTier.EXPOSURE  # pragma: no cover - unreachable, thresholds start at 0


# Complementary skill registry (drives recommendations)
@dataclass(frozen=True)
class ComplementRule:
    """
    One hand-curated pairing: if `trigger` is an established skill in the
    portfolio (tier above EXPOSURE) and none of `complements` is present at
    all, recommend `recommended`.

    Attributes:
        trigger: Skill name that activates this rule when established.
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
)
