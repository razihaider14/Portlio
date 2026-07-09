"""
Shared test helpers for the detector test suite.

f() : create a file entry
d() : create a directory entry
repo() : assemble entries into the dict shape detect_technologies() expects
"""


def f(path: str) -> dict:
    """Create a file entry with the given relative path."""
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "file"}


def d(path: str) -> dict:
    """Create a directory entry with the given relative path."""
    return {"path": path, "name": path.rsplit("/", 1)[-1], "type": "dir"}


def repo(*entries: dict, file_contents: dict | None = None) -> dict:
    """Assemble entry dicts into the repository shape the detector expects."""
    repository = {"contents": list(entries)}
    if file_contents is not None:
        repository["file_contents"] = file_contents
    return repository
