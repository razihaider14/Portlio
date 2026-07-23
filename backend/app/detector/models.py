"""
Core data models for the technology detector.
Entry : a single node in a repository's file tree.
Matcher : protocol for a single detection condition.
Rule : a named technology with a list of matchers (all must pass).
RuleCategory : the ecosystem a technology belongs to.
MatchResult : the output of a successful rule match, including metadata.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

# Maps an Entry.path (e.g. "requirements.txt") to its decoded text content.
# Only populated for the subset of files selected for download; see
# app.github.content_targets.CONTENT_TARGET_FILENAMES.
FileContents = dict[str, str]


class RuleCategory(str, Enum):
    """
    Broad ecosystem category for a technology rule.
    Used for filtering, grouping, and display. A single technology may only
    belong to one category; choose the most specific one that applies.
    """

    LANGUAGE = "language"  # Python, JavaScript, Rust, C++, ...
    FRAMEWORK = "framework"  # Django, Rails, Spring Boot, ...
    BUILD_SYSTEM = "build_system"  # CMake, Make, Gradle, ...
    PACKAGE_MANAGER = "package_manager"  # Poetry, npm, Composer, Cargo, ...
    FRONTEND = "frontend"  # HTML, CSS, Tailwind, Angular, ...
    MOBILE = "mobile"  # Flutter, React Native, Android, ...
    EMBEDDED = "embedded"  # Arduino, PlatformIO, ESP-IDF, ...
    CONTAINER = "container"  # Docker, Docker Compose, ...
    ORCHESTRATION = "orchestration"  # Kubernetes, Helm, ...
    CI_CD = "ci_cd"  # GitHub Actions, GitLab CI, ...
    DEVOPS = "devops"  # Terraform, Ansible, ...
    CLOUD = "cloud"  # AWS CDK, Serverless Framework, Pulumi, ...
    DATABASE = "database"  # Alembic, Prisma, Flyway, ...
    DATA_SCIENCE = "data_science"  # Jupyter, pandas, NumPy, ...
    ML_AI = "ml_ai"  # TensorFlow, PyTorch, Hugging Face Transformers, ...
    TESTING = "testing"  # pytest, Jest, JUnit, ...
    DOCUMENTATION = "documentation"  # Sphinx, MkDocs, Docusaurus, ...
    STATIC_ANALYSIS = "static_analysis"  # ESLint, Ruff, mypy, ...


class EvidenceStrength(str, Enum):
    """
    How strongly a matched Rule's signal proves the technology is actually
    used, as opposed to merely referenced, scaffolded, or declared as an
    intention.

    Authored per-Rule, by hand, the same way `confidence`/`priority`
    already are, not inferred dynamically from which individual Matcher
    inside a Rule's (possibly multi-matcher, AND-combined) condition
    happened to fire, since the engine only reports whether a Rule matched
    as a whole. A Rule combining more than one matcher type takes the
    strongest evidence class among them (e.g. a rule requiring both a
    dependency line AND a matching config file is at least CONFIGURED, not
    DECLARED), decided by the rule author at authoring time.

    DECLARED:
        The signal is a dependency-manifest entry only (e.g. a package
        name listed in requirements.txt/package.json/Cargo.toml, or a
        build-file substring equivalent to one, like "junit" appearing in
        a pom.xml). Proves intent to use the technology, not that any code
        actually exercises it, a dependency can be listed and never
        imported.
    CONFIGURED:
        A dedicated, non-trivial config file, config section, or vendored
        artifact exists and required deliberate setup beyond just listing
        a dependency (e.g. a `[tool.ruff]` pyproject.toml section, a
        vendored RTOS kernel directory). Stronger than a bare dependency
        line; still short of proof the surrounding code actually exercises
        the technology's behavior.
    DEMONSTRATED:
        A real, specific, hand-authored artifact or content match confirms
        the technology is actually in use: a source file written in the
        language/framework, a working CI pipeline definition, or matched
        file content confirming actual usage.

    See Phase 6 design decisions (2.1) in the Portlio Analysis Engine v2
    architecture document for the full rationale.
    """

    DECLARED = "declared"
    CONFIGURED = "configured"
    DEMONSTRATED = "demonstrated"


@dataclass(frozen=True)
class Entry:
    """
    A single file or directory in a repository's file tree.
    Attributes:
        path: Full relative path from the repo root. e.g. "src/main.py"
        name: Final path component (filename or directory name). e.g. "main.py"
        type: "file" or "dir".
    """

    path: str
    name: str
    type: str

    @property
    def extension(self) -> str:
        """
        Lowercase file extension including the leading dot. e.g. ".py"
        Returns an empty string if the filename has no extension.
        """
        _, dot, ext = self.name.rpartition(".")
        return f".{ext.lower()}" if dot else ""

    @property
    def is_file(self) -> bool:
        return self.type == "file"

    @property
    def is_dir(self) -> bool:
        return self.type == "dir"


@runtime_checkable
class Matcher(Protocol):
    """
    Protocol for a single detection condition.
    A matcher receives the complete, flat list of repository entries and
    an optional mapping of file contents, and returns True if its condition
    is satisfied. Within a single matcher, multiple candidate values use OR
    logic. Across matchers in a Rule, AND logic applies; all matchers must
    pass for the rule to trigger.
    Any class that implements
    `matches(entries: list[Entry], file_contents: FileContents | None) -> bool`
    satisfies this protocol without inheriting from it.

    file_contents maps an Entry.path to its decoded text content, and is
    only populated for the small set of files the GitHub client selects for
    download (see app.github.content_targets). It defaults to None/empty for
    matchers, callers, and tests that only care about tree structure,
    matchers that don't need file content simply ignore the parameter.
    """

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        """Return True if this condition is satisfied by the given entries."""
        ...


@dataclass
class Rule:
    """
    A technology detection rule.
    Attributes:
        name:       Display name of the technology. e.g. "Django"
        matchers:   All conditions that must be satisfied (AND logic).
        category:   The ecosystem this technology belongs to.
        confidence: How reliable the detection signal is (0.0 - 1.0).
                    1.0 means no false positives are expected.
                    Use lower values for heuristics or directory-name guesses.
        evidence_strength: How strongly this signal proves actual use
                    rather than mere declared intent; see EvidenceStrength.
                    Required, every rule author must explicitly classify
                    it rather than silently inheriting an unreviewed
                    default, since this value feeds skill-proficiency
                    scoring (app.aggregator).
        priority:   Relative ordering within a result set. Higher values
                    surface more specific technologies above general ones.
                    Suggested scale: language=10, package_manager=20,
                    framework=30, very_specific_tool=40.
    """

    name: str
    matchers: list[Matcher]
    category: RuleCategory
    evidence_strength: EvidenceStrength
    confidence: float = field(default=1.0)
    priority: int = field(default=0)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Rule '{self.name}': confidence must be between 0.0 and 1.0, "
                f"got {self.confidence}"
            )


@dataclass(frozen=True)
class MatchResult:
    """
    The output of a successfully matched Rule.
    Returned by the engine; the public detect_technologies() function
    distils this into a plain list[str] for backward compatibility.
    The richer form is available via detect_technologies_detailed().
    Attributes:
        name:       Technology name. e.g. "Django"
        category:   Ecosystem category.
        confidence: Reliability score from the matched Rule (0.0 – 1.0).
        evidence_strength: Copied from the matched Rule; see
                    EvidenceStrength.
        priority:   Ordering hint from the matched Rule.
    """

    name: str
    category: RuleCategory
    confidence: float
    evidence_strength: EvidenceStrength
    priority: int
