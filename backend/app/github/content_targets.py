"""
Registry of which repository files are worth downloading for content-based
technology detection and repository metadata analysis.

Kept separate from client.py so that adding, removing, or tuning which files
get fetched never requires touching HTTP/transport code. This registry is
shared infrastructure: both app.detector (dependency manifests, HasFileContent
markers) and app.metadata (README/LICENSE/CHANGELOG/CONTRIBUTING content) read
from it, so a file is only ever downloaded once no matter how many subsystems
want to look at it.
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
        # Community/project documentation files, used by app.metadata's
        # DocumentationQualityAnalyzer and LicenseAnalyzer. Common name
        # variants are listed explicitly rather than guessed, since GitHub
        # itself accepts several conventional spellings for each.
        "README.md",
        "README",
        "README.rst",
        "README.txt",
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "COPYING",
        "COPYING.md",
        "CHANGELOG.md",
        "CHANGELOG",
        "CHANGELOG.rst",
        "HISTORY.md",
        "CONTRIBUTING.md",
        "CONTRIBUTING",
        "CODE_OF_CONDUCT.md",
    )
)

# Files larger than this are skipped even if their name matches, to avoid
# spending a request budget on abnormally large READMEs or generated files.
MAX_CONTENT_FILE_SIZE_BYTES = 300_000

# Extensions (case-insensitive) that are worth downloading even though the
# filename itself varies per project, e.g. an Arduino sketch can be named
# anything, but always ends in .ino. Unlike CONTENT_TARGET_FILENAMES, a
# repository can have many files matching one of these, so each extension
# is capped (see MAX_MATCHES_PER_EXTENSION) to keep the request count
# bounded regardless of repo size.
CONTENT_TARGET_EXTENSIONS: frozenset[str] = frozenset({".ino"})

# Maximum number of files to select per extension in CONTENT_TARGET_EXTENSIONS.
# Shallower paths are preferred (a root-level sketch is more likely to be
# the primary one), then alphabetical, so the selection is deterministic.
MAX_MATCHES_PER_EXTENSION = 5

# Extensions for "companion" source files that get pulled in alongside a
# CONTENT_TARGET_EXTENSIONS match, but only from the same directory. This
# exists because a professionally structured Arduino/PlatformIO sketch
# often splits real logic (WiFi/Bluetooth setup, sensor drivers, etc.) into
# separate .cpp/.h files, leaving the .ino itself a thin wrapper around
# setup()/loop(), so scanning only the .ino can miss the evidence that
# actually identifies the target hardware platform.
CONTENT_TARGET_COMPANION_EXTENSIONS: frozenset[str] = frozenset(
    {".h", ".hpp", ".c", ".cpp"}
)

# Cap on companion files pulled in per directory, so a large firmware/ folder
# doesn't turn into dozens of requests. Alphabetical order keeps selection
# deterministic.
MAX_COMPANION_FILES_PER_DIRECTORY = 8


def _directory_of(path: str) -> str:
    return path.rsplit("/", 1)[0] if "/" in path else ""


def select_content_targets(
    entries: list[dict],
    filenames: frozenset[str] = CONTENT_TARGET_FILENAMES,
    max_size_bytes: int = MAX_CONTENT_FILE_SIZE_BYTES,
    extensions: frozenset[str] = CONTENT_TARGET_EXTENSIONS,
    max_matches_per_extension: int = MAX_MATCHES_PER_EXTENSION,
    companion_extensions: frozenset[str] = CONTENT_TARGET_COMPANION_EXTENSIONS,
    max_companion_files_per_directory: int = MAX_COMPANION_FILES_PER_DIRECTORY,
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
        extensions: Set of lowercase extensions to select regardless of
            filename. Defaults to CONTENT_TARGET_EXTENSIONS.
        max_matches_per_extension: Cap on how many files per extension get
            selected, so a repo with e.g. 50 .ino files doesn't turn into
            50 requests. Shallower paths win ties.
        companion_extensions: Extensions of "sibling" files to also select
            from any directory that contained an `extensions` match (e.g.
            .cpp/.h files next to a .ino sketch). Defaults to
            CONTENT_TARGET_COMPANION_EXTENSIONS.
        max_companion_files_per_directory: Cap on companion files selected
            per directory. Alphabetical order wins ties.

    Returns:
        The subset of `entries` that are files, whose name matches
        `filenames`, extension matches `extensions`, or are a companion
        file (see above), case-insensitive, and not oversized.
    """
    selected = []
    selected_paths: set[str] = set()

    for entry in entries:
        if entry.get("type") != "file":
            continue
        if entry.get("name", "").lower() not in filenames:
            continue
        size = entry.get("size")
        if size is not None and size > max_size_bytes:
            continue
        selected.append(entry)
        selected_paths.add(entry["path"])

    extension_match_directories: set[str] = set()
    for extension in extensions:
        candidates = [
            e
            for e in entries
            if e.get("type") == "file"
            and e.get("name", "").lower().endswith(extension)
            and (e.get("size") is None or e["size"] <= max_size_bytes)
        ]
        candidates.sort(key=lambda e: (e["path"].count("/"), e["path"].lower()))
        for entry in candidates[:max_matches_per_extension]:
            if entry["path"] not in selected_paths:
                selected.append(entry)
                selected_paths.add(entry["path"])
            extension_match_directories.add(_directory_of(entry["path"]))

    if companion_extensions:
        for directory in extension_match_directories:
            candidates = [
                e
                for e in entries
                if e.get("type") == "file"
                and e["path"] not in selected_paths
                and _directory_of(e["path"]) == directory
                and e.get("name", "").lower().endswith(tuple(companion_extensions))
                and (e.get("size") is None or e["size"] <= max_size_bytes)
            ]
            candidates.sort(key=lambda e: e["path"].lower())
            for entry in candidates[:max_companion_files_per_directory]:
                selected.append(entry)
                selected_paths.add(entry["path"])

    return selected
