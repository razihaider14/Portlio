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
    DATABASE = "database"  # Alembic, Prisma, Flyway, ...
    DATA_SCIENCE = "data_science"  # Jupyter, TensorFlow, ...
    TESTING = "testing"  # pytest, Jest, JUnit, ...


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
    logic. Across matchers in a Rule, AND logic applies : all matchers must
    pass for the rule to trigger.
    Any class that implements
    `matches(entries: list[Entry], file_contents: FileContents | None) -> bool`
    satisfies this protocol without inheriting from it.

    file_contents maps an Entry.path to its decoded text content, and is
    only populated for the small set of files the GitHub client selects for
    download (see app.github.content_targets). It defaults to None/empty for
    matchers, callers, and tests that only care about tree structure;
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
        priority:   Relative ordering within a result set. Higher values
                    surface more specific technologies above general ones.
                    Suggested scale: language=10, package_manager=20,
                    framework=30, very_specific_tool=40.
    """

    name: str
    matchers: list[Matcher]
    category: RuleCategory
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
        priority:   Ordering hint from the matched Rule.
    """

    name: str
    category: RuleCategory
    confidence: float
    priority: int
