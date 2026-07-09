"""
Registry of which repository files are worth downloading for content-based
technology detection.

Kept separate from client.py so that adding, removing, or tuning which files
get fetched never requires touching HTTP/transport code.
"""

# Filenames (case-insensitive, matched anywhere in the tree) that are useful
# for content-based detection: dependency manifests, lockfile-adjacent config,
# and project descriptors. Deliberately excludes large/binary lockfiles
# (poetry.lock, package-lock.json, ...) since their *presence* is already a
# strong-enough filename-based signal and their content isn't needed.
CONTENT_TARGET_FILENAMES: frozenset[str] = frozenset(
    name.lower()
    for name in (
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "Pipfile",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "composer.json",
        "Gemfile",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "mix.exs",
        "environment.yml",
        "README.md",
    )
)

# Files larger than this are skipped even if their name matches, to avoid
# spending a request budget on abnormally large READMEs or generated files.
MAX_CONTENT_FILE_SIZE_BYTES = 300_000


def select_content_targets(
    entries: list[dict],
    filenames: frozenset[str] = CONTENT_TARGET_FILENAMES,
    max_size_bytes: int = MAX_CONTENT_FILE_SIZE_BYTES,
) -> list[dict]:
    """
    Given the flat list of tree entries already fetched via the Git Trees
    API, pick out only the ones worth downloading for content inspection.

    This never issues a network request itself; it just filters data the
    caller already has, which is what keeps content downloading from
    costing more than one extra request per useful file (zero requests for
    files that turn out not to exist).

    Args:
        entries: Flat list of entry dicts (as returned by
            github.client.get_repository_tree), each with "path", "name",
            "type", and optionally "size".
        filenames: Set of lowercase filenames to select. Defaults to
            CONTENT_TARGET_FILENAMES.
        max_size_bytes: Entries with a known "size" larger than this are
            skipped. Entries with no "size" field are never skipped on
            this basis.

    Returns:
        The subset of `entries` that are files, whose name matches
        `filenames` (case-insensitive), and are not oversized.
    """
    selected = []
    for entry in entries:
        if entry.get("type") != "file":
            continue
        if entry.get("name", "").lower() not in filenames:
            continue
        size = entry.get("size")
        if size is not None and size > max_size_bytes:
            continue
        selected.append(entry)
    return selected
