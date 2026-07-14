"""
Detects whether the repository has an identifiable test suite, from test
directory conventions, test filename conventions, and declared test-framework
dependencies.
"""

from fnmatch import fnmatch

from app.metadata.dependency_utils import has_dependency
from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_directory

_TEST_DIRECTORIES = ("tests", "test", "spec", "__tests__")

_TEST_FILENAME_PATTERNS = (
    "test_*.py",
    "*_test.py",
    "*.test.js",
    "*.test.ts",
    "*.spec.js",
    "*.spec.ts",
    "*test.go",
    "*Test.java",
)

_TEST_FRAMEWORK_PACKAGES = (
    "pytest",
    "jest",
    "mocha",
    "vitest",
    "cypress",
    "playwright",
    "@playwright/test",
    "rspec",
    "phpunit/phpunit",
)


class TestPresenceAnalyzer:
    """Detects the presence of a test suite from deterministic conventions."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        evidence = []

        matched_dirs = [d for d in _TEST_DIRECTORIES if has_directory(input.entries, d)]
        evidence.extend(f"found {d}/ directory" for d in matched_dirs)

        matched_file_patterns = []
        for pattern in _TEST_FILENAME_PATTERNS:
            hit = any(
                e.get("type") == "file" and fnmatch(e["name"].lower(), pattern.lower())
                for e in input.entries
            )
            if hit:
                matched_file_patterns.append(pattern)
        evidence.extend(f"found files matching {p}" for p in matched_file_patterns)

        matched_frameworks = [
            p for p in _TEST_FRAMEWORK_PACKAGES if has_dependency(input, p)
        ]
        evidence.extend(f'declares dependency on "{p}"' for p in matched_frameworks)

        has_tests = bool(evidence)
        confidence = (
            0.95 if has_tests else 1.0
        )  # absence is as certain as presence here
        return [Finding("has_tests", has_tests, confidence, tuple(evidence))]
