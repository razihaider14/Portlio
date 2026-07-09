"""
Concrete Matcher implementations for the technology rule engine.
Primitive matchers inspect individual properties of repository entries:
    HasExtension : file extension
    HasFilename : exact filename (case-insensitive)
    HasDirectory : directory name (case-insensitive)
    HasPath : path prefix (case-insensitive)
    HasFileGlob : filename glob pattern

Content matchers inspect the decoded content of downloaded files (see
app.github.content_targets for which files get downloaded):
    HasFileContent : file content substring
    HasJsonKey : a dotted key path exists (optionally with a value) in a JSON file
    HasTomlSection : a dotted table path exists (optionally with a key) in a TOML file
    HasDependency : a package is declared as a dependency, across ecosystems

Composite matchers combine other matchers with boolean logic:
    AnyOf -> OR:  matches if any child matcher matches
    AllOf -> AND: matches if all child matchers match

All primitive matching is case-insensitive.
Candidate values within a single primitive matcher use OR logic.

Every matcher's matches() accepts an optional `file_contents` mapping of
path -> decoded text. Matchers that only need tree structure ignore it;
content matchers require it and simply don't match when it's absent
(e.g. when a caller hasn't opted into content downloading).
"""

import json
import tomllib
from dataclasses import dataclass
from fnmatch import fnmatch

from app.detector.dependency_parsers import (
    DEPENDENCY_PARSERS,
    normalize_dependency_name,
)
from app.detector.models import Entry, FileContents, Matcher

# Primitive matchers


@dataclass(frozen=True)
class HasExtension:
    """
    Matches if the tree contains at least one file whose extension
    is among the given extensions (case-insensitive).

    Example:
        HasExtension(".py")
        HasExtension(".c", ".cpp", ".h")
    """

    extensions: tuple[str, ...]

    def __init__(self, *extensions: str) -> None:
        object.__setattr__(self, "extensions", tuple(e.lower() for e in extensions))

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(e.is_file and e.extension in self.extensions for e in entries)


@dataclass(frozen=True)
class HasFilename:
    """
    Matches if the tree contains a file whose name exactly matches any of
    the given filenames (case-insensitive, anywhere in the tree).

    Example:
        HasFilename("Cargo.toml")
        HasFilename("docker-compose.yml", "docker-compose.yaml")
    """

    names: tuple[str, ...]

    def __init__(self, *names: str) -> None:
        object.__setattr__(self, "names", tuple(n.lower() for n in names))

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(e.is_file and e.name.lower() in self.names for e in entries)


@dataclass(frozen=True)
class HasDirectory:
    """
    Matches if the tree contains a directory whose name exactly matches any
    of the given names (case-insensitive, anywhere in the tree).

    Example:
        HasDirectory(".github")
        HasDirectory("k8s", "kubernetes")
    """

    names: tuple[str, ...]

    def __init__(self, *names: str) -> None:
        object.__setattr__(self, "names", tuple(n.lower() for n in names))

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(e.is_dir and e.name.lower() in self.names for e in entries)


@dataclass(frozen=True)
class HasPath:
    """
    Matches if any entry's full path starts with any of the given prefixes
    (case-insensitive).

    Useful for pinpointing files or directories at a known location in the
    tree, e.g. asserting that a Spring Boot resources directory exists, or
    that at least one workflow file lives inside .github/workflows/.

    Example:
        HasPath(".github/workflows")
        HasPath("src/main/resources/application.properties")
    """

    paths: tuple[str, ...]

    def __init__(self, *paths: str) -> None:
        object.__setattr__(self, "paths", tuple(p.lower() for p in paths))

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(
            e.path.lower().startswith(path) for path in self.paths for e in entries
        )


@dataclass(frozen=True)
class HasFileGlob:
    """
    Matches if any file in the tree has a name matching any of the given
    glob patterns (case-insensitive, fnmatch semantics).

    Unlike HasExtension (extension only) or HasFilename (exact name), this
    matches against the full filename with wildcard support in any position.

    A pattern with no wildcards behaves as a case-insensitive exact match.

    Example:
        HasFileGlob("dockerfile")      # Dockerfile, DOCKERFILE, etc.
        HasFileGlob("next.config.*")   # next.config.js, next.config.ts, ...
        HasFileGlob("test_*.py")       # pytest test files
        HasFileGlob("jenkinsfile*")    # Jenkinsfile, Jenkinsfile.groovy
    """

    patterns: tuple[str, ...]

    def __init__(self, *patterns: str) -> None:
        object.__setattr__(self, "patterns", tuple(p.lower() for p in patterns))

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(
            e.is_file and any(fnmatch(e.name.lower(), p) for p in self.patterns)
            for e in entries
        )


@dataclass(frozen=True)
class HasFileContent:
    """
    Matches if a file with the given name exists in the tree and its
    downloaded content contains the given substring (case-insensitive).

    Requires `file_contents` to be supplied (see
    app.github.client.get_repository_file_contents); if it's absent or the
    target file wasn't downloaded, this never matches : it does not raise.

    Example:
        HasFileContent("requirements.txt", "fastapi")
        HasFileContent("package.json", '"react"')
        HasFileContent("pom.xml", "spring-boot")
    """

    filename: str
    contains: str

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        if not file_contents:
            return False
        target_name = self.filename.lower()
        needle = self.contains.lower()
        for entry in entries:
            if not entry.is_file or entry.name.lower() != target_name:
                continue
            content = file_contents.get(entry.path)
            if content and needle in content.lower():
                return True
        return False


@dataclass(frozen=True)
class HasJsonKey:
    """
    Matches if a JSON file with the given name exists in the tree, is
    downloaded and parses successfully, and contains the given dotted key
    path.

    If `contains` is given, the resolved value must additionally either
    equal it, contain it as a substring (for string values), or contain it
    as a member (for list/dict values), all compared case-insensitively
    for strings. If `contains` is omitted, matching the key path's presence
    is sufficient.

    Malformed JSON, or a file that wasn't downloaded, never matches (no
    exception is raised).

    Example:
        HasJsonKey("package.json", "dependencies.react")
        HasJsonKey("package.json", "scripts.build", contains="webpack")
    """

    filename: str
    key_path: str
    contains: str | None = None

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        if not file_contents:
            return False
        target_name = self.filename.lower()
        for entry in entries:
            if not entry.is_file or entry.name.lower() != target_name:
                continue
            content = file_contents.get(entry.path)
            if not content:
                continue
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                continue
            found, value = _resolve_dotted_path(data, self.key_path)
            if not found:
                continue
            if self.contains is None:
                return True
            if _value_contains(value, self.contains):
                return True
        return False


@dataclass(frozen=True)
class HasTomlSection:
    """
    Matches if a TOML file with the given name exists in the tree, is
    downloaded and parses successfully, and contains the given dotted table
    path (e.g. "tool.poetry.dependencies" or "dependencies").

    If `key` is given, that key must additionally be present within the
    resolved table. If omitted, the table's presence is sufficient.

    Malformed TOML, or a file that wasn't downloaded, never matches (no
    exception is raised).

    Example:
        HasTomlSection("Cargo.toml", "dependencies")
        HasTomlSection("pyproject.toml", "tool.poetry.dependencies", key="fastapi")
    """

    filename: str
    section_path: str
    key: str | None = None

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        if not file_contents:
            return False
        target_name = self.filename.lower()
        for entry in entries:
            if not entry.is_file or entry.name.lower() != target_name:
                continue
            content = file_contents.get(entry.path)
            if not content:
                continue
            try:
                data = tomllib.loads(content)
            except tomllib.TOMLDecodeError:
                continue
            found, value = _resolve_dotted_path(data, self.section_path)
            if not found:
                continue
            if self.key is None:
                return True
            if isinstance(value, dict) and self.key in value:
                return True
        return False


@dataclass(frozen=True)
class HasDependency:
    """
    Matches if the given package is declared as a dependency in any
    downloaded manifest file, across ecosystems (requirements.txt,
    pyproject.toml, package.json, Cargo.toml, go.mod, composer.json,
    Gemfile; see app.detector.dependency_parsers.DEPENDENCY_PARSERS for
    the authoritative list).

    Package name comparison is normalized (case-folded, "_"/"."/"-"
    treated as equivalent) so it works across ecosystems with different
    naming conventions. For Go modules, both the short name (last path
    segment) and the fully-qualified module path are checked.

    A manifest that fails to parse is skipped, not treated as an error.

    Example:
        HasDependency("fastapi")
        HasDependency("react")
        HasDependency("django-rest-framework")
    """

    package: str

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        if not file_contents:
            return False
        target = normalize_dependency_name(self.package)
        for entry in entries:
            if not entry.is_file:
                continue
            parser = DEPENDENCY_PARSERS.get(entry.name.lower())
            if parser is None:
                continue
            content = file_contents.get(entry.path)
            if not content:
                continue
            try:
                declared = parser(content)
            except Exception:
                continue
            if any(normalize_dependency_name(name) == target for name in declared):
                return True
        return False


def _resolve_dotted_path(data: dict, dotted_path: str) -> tuple[bool, object]:
    """
    Walk a dict through a dotted key path (e.g. "tool.poetry.dependencies").
    Returns (True, value) if the full path resolves through nested dicts,
    otherwise (False, None).
    """
    current = data
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _value_contains(value: object, needle: str) -> bool:
    """Case-insensitive containment check across common JSON value shapes."""
    needle_lower = needle.lower()
    if isinstance(value, str):
        return needle_lower in value.lower()
    if isinstance(value, dict):
        return any(str(k).lower() == needle_lower for k in value)
    if isinstance(value, (list, tuple, set)):
        return any(
            isinstance(item, str) and item.lower() == needle_lower for item in value
        )
    return str(value).lower() == needle_lower


# Composite matchers


@dataclass(frozen=True)
class AnyOf:
    """
    Composite matcher: matches if ANY of the given matchers match (OR logic).

    Use when a technology can be identified by multiple alternative signals
    and you want to express the alternatives inside a single rule, rather than
    duplicating the rule.

    Example : detect a JVM build file of any kind:
        AnyOf(HasFilename("pom.xml"), HasFilename("build.gradle"))

    Example : nested inside a rule alongside other matchers:
        Rule(
            name="Spring Boot",
            matchers=[
                AnyOf(HasFilename("pom.xml"), HasFilename("build.gradle")),
                HasPath("src/main/resources/application.properties"),
            ],
        )
    """

    matchers: tuple[Matcher, ...]

    def __init__(self, *matchers: Matcher) -> None:
        object.__setattr__(self, "matchers", matchers)

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return any(m.matches(entries, file_contents) for m in self.matchers)


@dataclass(frozen=True)
class AllOf:
    """
    Composite matcher: matches if ALL of the given matchers match (AND logic).

    Equivalent to listing matchers at the Rule level, but useful for grouping
    a sub-condition set inside an AnyOf, enabling full nested boolean logic.

    Example : Spring Boot detected via either Maven or Gradle, each paired
    with its own config file signal:
        AnyOf(
            AllOf(
                HasFilename("pom.xml"),
                HasPath("src/main/resources/application.properties"),
            ),
            AllOf(
                HasFilename("build.gradle"),
                HasPath("src/main/resources/application.properties"),
            ),
        )
    """

    matchers: tuple[Matcher, ...]

    def __init__(self, *matchers: Matcher) -> None:
        object.__setattr__(self, "matchers", matchers)

    def matches(
        self, entries: list[Entry], file_contents: FileContents | None = None
    ) -> bool:
        return all(m.matches(entries, file_contents) for m in self.matchers)
