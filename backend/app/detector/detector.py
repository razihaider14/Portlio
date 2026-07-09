"""
Public API for the technology detector.

External callers use detect_technologies() for the stable list[str] interface,
or detect_technologies_detailed() for the richer MatchResult form.

Internal modules (engine, matchers, models, rules) are implementation details
and should not be imported directly by code outside app/detector/.
"""

from app.detector.engine import detect
from app.detector.models import Entry, MatchResult
from app.detector.rules import RULES


def _to_entries(repository: dict) -> list[Entry]:
    """Convert the raw repository dict to typed Entry objects."""
    return [
        Entry(path=item["path"], name=item["name"], type=item["type"])
        for item in repository.get("contents") or []
    ]


def detect_technologies(repository: dict) -> list[str]:
    """
    Inspect a repository's contents and return a sorted list of detected
    technology names.

    This is the stable public API. The return value is always a sorted list
    of strings, regardless of internal engine changes.

    Args:
        repository: a dict containing:
            "contents": list of entry dicts, each with "path", "name", "type".
            "file_contents" (optional): dict mapping a path from "contents"
                to its decoded text content, enabling content-based matchers
                (HasFileContent, HasDependency, ...). Omit or leave empty to
                match today's tree-only behavior exactly.

    Returns:
        Alphabetically sorted list of detected technology names.
    """
    results = detect(_to_entries(repository), RULES, repository.get("file_contents"))
    return sorted(r.name for r in results)


def detect_technologies_detailed(repository: dict) -> list[MatchResult]:
    """
    Inspect a repository's contents and return full MatchResult objects,
    including category, confidence, and priority for each detection.

    Results are sorted by priority (descending), then alphabetically by name.

    Args:
        repository: a dict containing:
            "contents": list of entry dicts, each with "path", "name", "type".
            "file_contents" (optional): dict mapping a path from "contents"
                to its decoded text content; see detect_technologies().

    Returns:
        List of MatchResult objects, sorted by priority descending then name.
    """
    results = detect(_to_entries(repository), RULES, repository.get("file_contents"))
    return sorted(results, key=lambda r: (-r.priority, r.name))
