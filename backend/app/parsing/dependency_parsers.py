"""
Best-effort dependency-name extraction from common manifest formats.

Kept separate from matchers.py so that matchers.py stays focused on the
matching contract (Entry list + file content in, bool out) while the messy
per-ecosystem parsing details live here. Each parser takes raw file text and
returns a set of dependency names as declared in the manifest, normalization
(case, separators) is handled by the caller (see HasDependency), not here.

Every parser is best-effort: malformed input should yield a smaller-than-
expected set rather than raise, so callers should still wrap calls in
try/except for genuinely unparseable content (e.g. truncated downloads).
"""

import json
import re
import tomllib


def parse_requirements_txt(content: str) -> set[str]:
    """Extract package names from a pip requirements.txt-style file."""
    names: set[str] = set()
    for line in content.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r ", "-e ", "--")):
            continue
        # Stop at the first version/marker/extras delimiter.
        match = re.match(r"^([A-Za-z0-9_.\-]+)", line)
        if match:
            names.add(match.group(1))
    return names


def _extract_pep508_name(requirement: str) -> str | None:
    """Extract the package name from a PEP 508 requirement string."""
    match = re.match(r"^\s*([A-Za-z0-9_.\-]+)", requirement)
    return match.group(1) if match else None


def parse_pyproject_toml(content: str) -> set[str]:
    """
    Extract dependency names from pyproject.toml, covering both the
    PEP 621 [project] table and Poetry's [tool.poetry] tables.
    """
    data = tomllib.loads(content)
    names: set[str] = set()

    project = data.get("project", {})
    for requirement in project.get("dependencies", []):
        name = _extract_pep508_name(requirement)
        if name:
            names.add(name)
    for group in project.get("optional-dependencies", {}).values():
        for requirement in group:
            name = _extract_pep508_name(requirement)
            if name:
                names.add(name)

    poetry = data.get("tool", {}).get("poetry", {})
    for section_name in ("dependencies", "dev-dependencies"):
        for name in poetry.get(section_name, {}):
            if name.lower() != "python":
                names.add(name)
    for group in poetry.get("group", {}).values():
        for name in group.get("dependencies", {}):
            if name.lower() != "python":
                names.add(name)

    return names


def parse_package_json(content: str) -> set[str]:
    """Extract dependency names from package.json."""
    data = json.loads(content)
    names: set[str] = set()
    for key in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        names.update(data.get(key, {}).keys())
    return names


def parse_cargo_toml(content: str) -> set[str]:
    """Extract dependency names from Cargo.toml."""
    data = tomllib.loads(content)
    names: set[str] = set()
    for section_name in ("dependencies", "dev-dependencies", "build-dependencies"):
        names.update(data.get(section_name, {}).keys())
    for target in data.get("target", {}).values():
        for section_name in ("dependencies", "dev-dependencies", "build-dependencies"):
            names.update(target.get(section_name, {}).keys())
    return names


_GO_VERSION_SEGMENT = re.compile(r"^v[0-9]+$")


def parse_go_mod(content: str) -> set[str]:
    """
    Extract required module paths from go.mod, along with each module's
    "short" name (the last path segment, ignoring a trailing major-version
    segment like "/v2" or "/v4" per Go's module versioning convention) so
    that lookups can use either the short or fully-qualified name.

    e.g. "github.com/gofiber/fiber/v2" yields both the full path and "fiber"
    (not "v2", which a naive last-segment split would produce).
    """
    names: set[str] = set()
    in_require_block = False
    for raw_line in content.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if line.startswith("require") and line.endswith("("):
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue

        module_path = None
        if in_require_block:
            match = re.match(r"^([^\s]+)\s+v", line)
            if match:
                module_path = match.group(1)
        elif line.startswith("require "):
            match = re.match(r"^require\s+([^\s]+)\s+v", line)
            if match:
                module_path = match.group(1)

        if module_path:
            names.add(module_path)
            segments = module_path.split("/")
            short = segments[-1]
            if _GO_VERSION_SEGMENT.match(short) and len(segments) > 1:
                short = segments[-2]
            names.add(short)
    return names


def parse_composer_json(content: str) -> set[str]:
    """Extract dependency names from composer.json."""
    data = json.loads(content)
    names: set[str] = set()
    for key in ("require", "require-dev"):
        for name in data.get(key, {}):
            if name.lower() != "php":
                names.add(name)
    return names


def parse_gemfile(content: str) -> set[str]:
    """Extract gem names from a Ruby Gemfile."""
    return set(re.findall(r"""gem\s+['"]([^'"]+)['"]""", content))


# Registry mapping a lowercase manifest filename to its parser. This is the
# single place a new ecosystem needs to be wired in for HasDependency to
# pick it up automatically.
DEPENDENCY_PARSERS = {
    "requirements.txt": parse_requirements_txt,
    "requirements-dev.txt": parse_requirements_txt,
    "pyproject.toml": parse_pyproject_toml,
    "package.json": parse_package_json,
    "cargo.toml": parse_cargo_toml,
    "go.mod": parse_go_mod,
    "composer.json": parse_composer_json,
    "gemfile": parse_gemfile,
}


def normalize_dependency_name(name: str) -> str:
    """
    Normalize a dependency name for comparison across ecosystems that use
    different casing/separator conventions (e.g. PyPI's "Django-Rest-Framework"
    vs npm's "django-rest-framework"). Case-folds and treats "_" and "." the
    same as "-", matching PEP 503 normalization for Python packages while
    remaining harmless for other ecosystems.
    """
    return re.sub(r"[-_.]+", "-", name.strip().lower())
