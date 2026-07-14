"""
Public API for the repository metadata analyzer.

Mirrors app.detector.detector: a stable two-tier public API on top of an
internal engine, so callers get either a friendly flattened result or a
richer form with confidence and evidence, without needing to know how many
analyzers exist or how they're implemented.
"""

import copy

from app.metadata.analyzers import ANALYZERS
from app.metadata.engine import analyze
from app.metadata.models import AnalysisInput, Finding

# Fields that are inherently multi-valued: a repository can have several
# project types, hardware platforms, CI providers, package managers, or
# build systems at once, so these always fold to a list (possibly empty),
# never a bare scalar.
_LIST_FIELDS = frozenset(
    {
        "project_types",
        "hardware_platforms",
        "ci_providers",
        "package_managers",
        "build_systems",
    }
)

# The complete, stable set of fields analyze_repository_metadata() always
# returns, with their empty/default value when no analyzer had anything to
# say. Keeping this explicit (rather than only including keys that got a
# Finding) means callers can rely on every key always being present,
# important for "future skill aggregation" consumers that index into the
# result without checking for KeyError first.
_FIELD_DEFAULTS: dict[str, object] = {
    "project_types": [],
    "hardware_platforms": [],
    "documentation": {
        "has_readme": False,
        "has_license_file": False,
        "has_changelog": False,
        "has_contributing": False,
        "has_code_of_conduct": False,
        "readme_length_chars": None,
        "readme_heading_count": 0,
        "readme_sections": [],
        "score": 0,
        "quality_tier": "none",
    },
    "has_tests": False,
    "has_ci_cd": False,
    "ci_providers": [],
    "has_docker": False,
    "has_docker_compose": False,
    "has_kubernetes_manifests": False,
    "package_managers": [],
    "build_systems": [],
    "license": {"detected": False, "spdx_id": None, "source": None},
    "maturity": {
        "stars": 0,
        "forks": 0,
        "open_issues": 0,
        "age_days": None,
        "days_since_last_push": None,
        "is_archived": False,
        "is_fork": False,
        "maturity_tier": "unknown",
    },
    "size_metrics": {
        "total_files": 0,
        "total_directories": 0,
        "file_count_by_extension": {},
        "max_directory_depth": 0,
        "repo_size_kb": None,
    },
}


def _to_input(repository: dict) -> AnalysisInput:
    return AnalysisInput(
        entries=repository.get("contents", []),
        file_contents=repository.get("file_contents") or {},
        repo_metadata=repository.get("repo_metadata") or {},
    )


def _fold(findings: list[Finding]) -> dict:
    """Group Findings by field into the stable, always-complete output shape."""
    result = copy.deepcopy(_FIELD_DEFAULTS)
    for finding in findings:
        if finding.field in _LIST_FIELDS:
            result[finding.field].append(finding.value)
        else:
            # Scalar/dict fields: each analyzer contributing to one of these
            # emits exactly one Finding, so the latest (only) one wins.
            result[finding.field] = finding.value
    return result


def analyze_repository_metadata(repository: dict) -> dict:
    """
    Inspect a repository's tree, downloaded documentation content, and raw
    GitHub repo metadata to infer deterministic repository characteristics.

    This is the stable public API: the return value always has exactly the
    keys in _FIELD_DEFAULTS, regardless of internal analyzer changes.

    Args:
        repository: a dict containing:
            "contents": list of entry dicts (path/name/type[/size]).
            "file_contents" (optional): dict mapping a path from "contents"
                to its decoded text content, richer results (README
                structure, license text matching) become available when
                README/LICENSE/CHANGELOG/CONTRIBUTING content is present.
            "repo_metadata" (optional): dict of raw GitHub repository API
                fields (stargazers_count, forks_count, created_at,
                pushed_at, size, archived, fork, license, ...), powers the
                license and maturity fields.

    Returns:
        A flat dict with one key per metadata field (see _FIELD_DEFAULTS
        for the complete, stable list of keys and their shapes).
    """
    findings = analyze(_to_input(repository), ANALYZERS)
    return _fold(findings)


def analyze_repository_metadata_detailed(repository: dict) -> list[Finding]:
    """
    Same inputs as analyze_repository_metadata(), but returns the raw
    Finding objects, including per-finding confidence and evidence,
    for callers that want provenance rather than just the folded values.
    """
    return analyze(_to_input(repository), ANALYZERS)
