"""
Shared "does this repo declare dependency X" helper for metadata analyzers.

Several analyzers (project type, hardware platform, testing) need to check
manifest files for a specific declared package. This wraps
app.parsing.dependency_parsers; a stateless, subsystem-agnostic parsing
utility also used by the technology detector, without importing anything
from app.detector itself.
"""

from app.metadata.models import AnalysisInput
from app.parsing.dependency_parsers import DEPENDENCY_PARSERS, normalize_dependency_name


def has_dependency(input: AnalysisInput, *package_names: str) -> bool:
    """
    True if any of `package_names` is declared in any downloaded manifest
    file present in `input` (requirements.txt, pyproject.toml, package.json,
    Cargo.toml, go.mod, composer.json, Gemfile; see DEPENDENCY_PARSERS).

    Returns False (never raises) if content wasn't downloaded, or if a
    manifest present fails to parse.
    """
    if not input.file_contents:
        return False
    wanted = {normalize_dependency_name(name) for name in package_names}
    for entry in input.entries:
        if entry.get("type") != "file":
            continue
        parser = DEPENDENCY_PARSERS.get(entry["name"].lower())
        if parser is None:
            continue
        content = input.file_contents.get(entry["path"])
        if not content:
            continue
        try:
            declared = parser(content)
        except Exception:
            continue
        if any(normalize_dependency_name(name) in wanted for name in declared):
            return True
    return False
