"""
Data models for the repository metadata analyzer.

Mirrors app.detector.models in spirit (a small typed core plus a uniform
plug-in contract) but is intentionally self-contained: nothing here imports
from app.detector. The two subsystems answer different questions,
"what technologies does this repo use" vs. "what kind of repo is this, and
how mature/documented/tested is it", and are wired together only at the
app.analyzer orchestration layer, not at the model or engine level.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AnalysisInput:
    """
    Everything a metadata Analyzer is allowed to look at.

    Deliberately plain dicts (not app.detector.models.Entry) so this
    subsystem has zero dependency on the detector: entries carry whatever
    keys app.github.client.get_repository_tree() already returns (path,
    name, type, and optionally size).

    Attributes:
        entries: Flat list of repository tree entries (dicts with at least
            "path", "name", "type", and optionally "size").
        file_contents: Decoded text content for downloaded files, keyed by
            path (see app.github.content_targets). Empty if content
            downloading wasn't requested; analyzers must degrade to
            presence-only facts, not raise, when this is empty.
        repo_metadata: Raw repository fields from the GitHub API's repo
            object (stargazers_count, forks_count, created_at, pushed_at,
            size, archived, fork, license, topics, ...). Empty dict if
            unavailable.
    """

    entries: list[dict]
    file_contents: dict[str, str] = field(default_factory=dict)
    repo_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """
    One piece of metadata contributed by an Analyzer.

    Attributes:
        field: Output key this finding belongs under, e.g. "project_types",
            "has_tests", "license". Multiple Findings may share a field
            (e.g. several detected hardware platforms); the engine and
            public API group them, see app.metadata.metadata_analyzer.
        value: The actual data; a bool, str, int, float, dict, or list,
            depending on the field. See FIELD_SPECS in metadata_analyzer.py
            for the authoritative shape of every field.
        confidence: 0.0-1.0. 1.0 means the value is an exact fact (a count,
            a GitHub API field, an unambiguous config filename). Lower
            values indicate an inference from indirect but still
            deterministic evidence (e.g. classifying "library" by the
            absence of app-like markers).
        evidence: Short, human-readable reasons supporting this finding,
            e.g. ("found platformio.ini", "found 3 .ino files"). Intended
            for debugging and for any future skill that wants to explain
            itself, not for display logic to depend on their exact wording.
    """

    field: str
    value: Any
    confidence: float
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Finding for '{self.field}': confidence must be between "
                f"0.0 and 1.0, got {self.confidence}"
            )


@runtime_checkable
class Analyzer(Protocol):
    """
    Protocol for a single metadata analyzer.

    An Analyzer receives the complete AnalysisInput and returns zero or
    more Findings. Returning an empty list means "no opinion", e.g. a
    hardware-platform analyzer looking at a pure web app returns [], not a
    zero-confidence guess. Any class implementing
    `analyze(input: AnalysisInput) -> list[Finding]` satisfies this
    protocol without inheriting from it, mirroring app.detector.models.Matcher.
    """

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        """Return zero or more Findings inferred from `input`."""
        ...
