"""
Detects build system(s) in use from exclusive build config filenames.
"""

from app.metadata.models import AnalysisInput, Finding
from app.metadata.tree_utils import has_filename, has_glob

# (build system name, filenames, glob patterns)
_FILENAME_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("CMake", ("CMakeLists.txt",)),
    ("Make", ("Makefile", "makefile")),
    ("Maven", ("pom.xml",)),
    ("Gradle", ("build.gradle", "build.gradle.kts")),
    ("Bazel", ("WORKSPACE", "WORKSPACE.bazel", "BUILD.bazel")),
    ("Ninja", ("build.ninja",)),
    ("Meson", ("meson.build",)),
)
_GLOB_MARKERS: tuple[tuple[str, str], ...] = (
    ("Webpack", "webpack.config.*"),
    ("Vite", "vite.config.*"),
)


class BuildSystemAnalyzer:
    """Detects build system(s) from exclusive build config filenames."""

    def analyze(self, input: AnalysisInput) -> list[Finding]:
        findings = []
        for name, filenames in _FILENAME_MARKERS:
            matched = [f for f in filenames if has_filename(input.entries, f)]
            if matched:
                findings.append(
                    Finding(
                        "build_systems", name, 1.0, tuple(f"found {f}" for f in matched)
                    )
                )
        for name, pattern in _GLOB_MARKERS:
            if has_glob(input.entries, pattern):
                findings.append(
                    Finding(
                        "build_systems", name, 1.0, (f"found file matching {pattern}",)
                    )
                )
        return findings
