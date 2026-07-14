"""
Small, pure helper functions for inspecting the raw tree-entry dicts in
AnalysisInput.entries.

These are the metadata subsystem's equivalent of app.detector.matchers'
primitive matchers, but as plain functions rather than dataclasses, an
analyzer typically needs to ask several different presence questions in one
pass (e.g. "is there a tests/ dir AND are there test_*.py files"), which
reads more naturally as function calls than as instantiated matcher objects.
Nothing here imports from app.detector.
"""

from fnmatch import fnmatch


def filenames(entries: list[dict]) -> set[str]:
    """Lowercase names of every file entry (not directories)."""
    return {e["name"].lower() for e in entries if e.get("type") == "file"}


def directory_names(entries: list[dict]) -> set[str]:
    """Lowercase names of every directory entry."""
    return {e["name"].lower() for e in entries if e.get("type") == "dir"}


def has_filename(entries: list[dict], *names: str) -> bool:
    """True if any file entry's name exactly matches one of `names` (case-insensitive)."""
    wanted = {n.lower() for n in names}
    return any(e.get("type") == "file" and e["name"].lower() in wanted for e in entries)


def has_extension(entries: list[dict], *extensions: str) -> bool:
    """
    True if any file entry ends with one of `extensions` (case-insensitive).
    Extensions should include the leading dot, e.g. ".py". Matches the full
    trailing string, so multi-part extensions like ".pkr.hcl" work correctly
    (unlike a naive rpartition(".") split).
    """
    wanted = tuple(ext.lower() for ext in extensions)
    return any(
        e.get("type") == "file" and e["name"].lower().endswith(wanted) for e in entries
    )


def has_directory(entries: list[dict], *names: str) -> bool:
    """True if any directory entry's name exactly matches one of `names` (case-insensitive)."""
    wanted = {n.lower() for n in names}
    return any(e.get("type") == "dir" and e["name"].lower() in wanted for e in entries)


def has_glob(entries: list[dict], pattern: str) -> bool:
    """True if any file entry's name matches the glob `pattern` (case-insensitive)."""
    pattern = pattern.lower()
    return any(
        e.get("type") == "file" and fnmatch(e["name"].lower(), pattern) for e in entries
    )


def matching_files(entries: list[dict], pattern: str) -> list[dict]:
    """All file entries whose name matches the glob `pattern` (case-insensitive)."""
    pattern = pattern.lower()
    return [
        e
        for e in entries
        if e.get("type") == "file" and fnmatch(e["name"].lower(), pattern)
    ]


def get_content(
    input_entries_map: dict[str, str], entries: list[dict], *filenames_: str
) -> str | None:
    """
    Return the downloaded content of the first file entry whose name matches
    one of `filenames_` (case-insensitive), or None if no such entry exists
    or its content wasn't downloaded.
    """
    wanted = {n.lower() for n in filenames_}
    for entry in entries:
        if entry.get("type") == "file" and entry["name"].lower() in wanted:
            content = input_entries_map.get(entry["path"])
            if content is not None:
                return content
    return None
